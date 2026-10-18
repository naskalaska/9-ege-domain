import csv
import io
import unittest
import uuid
import json
import shutil
import subprocess
import test_learning as fixtures
import server
import learning_module
import statistics_module as statistics
from attempt_content import describe_question


class StatisticsTest(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.LearningTest()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.teacher,self.student = self.case.teacher,self.case.student

    def add_attempt(self, activity='ege9', correct=False, prompt='Проверка слова', mode='mix',
                    word_id=None, question_id=None, created='2026-10-18T12:00:00+00:00'):
        with server.db() as con:
            con.execute('''INSERT INTO attempts(attempt_id,user_id,mode,scope_id,word_id,rule_id,category,
              rule_name,question_id,prompt,given_answer,correct_answer,is_correct,created_at)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (uuid.uuid4().hex,self.student['user_id'],mode,activity+':mix',word_id,'topic','Тема','Проверяемая тема',
               question_id or uuid.uuid4().hex,prompt,'и' if correct else 'о','и',int(correct),created))

    def test_full_history_pagination_export_and_filters(self):
        for n in range(127):
            self.add_attempt('ege10' if n%2 else 'ege9',n%3==0,prompt=f'Задание №{n}: Ёлочка')
        data = statistics.overview(server,self.student)
        self.assertEqual(data['summary']['total'],127)
        self.assertEqual(data['summary']['correct'],43)
        self.assertEqual(len([r for r in data['by_activity'] if r['activity'].startswith('ege')]),8)
        ids=[]
        for page in range(1,6):
            data=statistics.history(server,self.teacher,{'student_id':self.student['user_id'],'page':page})
            ids += [r['attempt_id'] for r in data['items']]
        self.assertEqual(len(ids),127)
        self.assertEqual(len(set(ids)),127)
        errors=statistics.history(server,self.teacher,{'status':'incorrect','activity':'ege10','search':'ёлОЧка'})
        self.assertEqual(errors['total'],42)
        body,_,_=statistics.export(server,self.teacher,{'student_id':self.student['user_id']})
        self.assertEqual(len(list(csv.reader(io.StringIO(body.decode('utf-8-sig')),delimiter=';'))),128)
        self.assertEqual(statistics.history(server,self.student,{'from':'2026-10-19'})['total'],0)
        self.add_attempt(created='2026-10-18T22:30:00+00:00')
        self.assertEqual(statistics.history(server,self.student,{'from':'2026-10-19','offset_minutes':'180'})['total'],1)
        self.assertEqual(statistics.history(server,self.student,{'from':'2026-10-19'})['total'],0)
        with self.assertRaises(ValueError): statistics.history(server,self.student,{'from':'not a date'})

    def test_ownership_and_empty_student(self):
        for action in (statistics.overview,statistics.history,statistics.export):
            with self.assertRaises(PermissionError):action(server,self.student,{'student_id':'another-student'})
            with self.assertRaises(PermissionError):action(server,self.teacher,{'student_id':'another-student'})
        data=statistics.overview(server,self.teacher)
        self.assertEqual(len(data['students']),1)
        self.assertEqual(data['students'][0]['total'],0)
        self.assertIsNone(data['students'][0]['accuracy'])

    def test_line_word_details_do_not_inflate_solutions_and_prompt_is_complete(self):
        test=self.case.create({'activity':'ege9','mode':'line','count':1})
        snap=self.case.snapshots(test['id'])[0]
        learning_module.check_question(server,self.student,{'test_id':test['id'],'question_id':snap['question_id'],
            'answer':snap['question']['correct_answer']})
        summary=statistics.overview(server,self.student)['summary']
        self.assertEqual((summary['total'],summary['correct']),(1,1))
        self.assertEqual(statistics.history(server,self.student,{'kind':'details'})['total'],15)
        actual=statistics.history(server,self.student,{'kind':'answers'})['items'][0]
        self.assertIn(snap['public']['rows'][0][0],actual['prompt'])
        self.assertIn('5)',actual['prompt'])
        # Older assigned attempts retained their frozen questions, even if the
        # attempt itself only saved an instruction.
        with server.db() as con:
            con.execute('UPDATE attempts SET prompt=? WHERE question_id=?',('Только инструкция',snap['question_id']))
        restored=statistics.history(server,self.student,{'kind':'answers'})['items'][0]
        self.assertIn(snap['public']['rows'][4][0],restored['prompt'])

    def test_game_errors_and_strengths_across_activities(self):
        for n in range(5):self.add_attempt('ege12',True)
        self.add_attempt('ege14',False)
        learning_module.game_result(server,self.student,{'slug':'autumn-leaves','event_id':'error-1','is_correct':False,
            'prompt':'ц..плёнок','given_answer':'и','correct_answer':'ы'})
        data=statistics.overview(server,self.teacher)
        self.assertEqual(data['summary']['total'],7)
        self.assertEqual(data['strengths'][0]['activity'],'ege12')
        self.assertEqual(data['students'][0]['errors'],2)
        game=statistics.history(server,self.teacher,{'activity':'games','status':'incorrect'})
        self.assertEqual(game['total'],1)
        self.assertEqual((game['items'][0]['prompt'],game['items'][0]['given_answer'],game['items'][0]['correct_answer']),('ц..плёнок','и','ы'))
        self.assertTrue(game['items'][0]['content_available'])

    def test_legacy_unprefixed_details_classified_by_word(self):
        word=server.ege11_module.WORDS[0]
        self.add_attempt('ege9',False,mode='line:line_word',word_id=word['id'])
        with server.db() as con:con.execute("UPDATE attempts SET scope_id='errors:bank'")
        data=statistics.history(server,self.student,{'activity':'ege11'})
        self.assertEqual(data['total'],1)
        self.assertEqual(data['items'][0]['correct_spelling'],word['correct_spelling'])
        self.assertEqual(statistics.overview(server,self.student)['summary']['total'],0)

    def test_assigned_contents_and_csv_keep_complete_text(self):
        self.add_attempt(prompt='=текст\nвторая строка')
        body,_,_=statistics.export(server,self.student)
        rows=list(csv.reader(io.StringIO(body.decode('utf-8-sig')),delimiter=';'))
        self.assertEqual(rows[1][4],"'=текст\nвторая строка")
        self.assertEqual(describe_question({'prompt':'Н/НН','parts':[{'text':'Дом '},{'target':{'label':'построе..ый'}}]}),'Н/НН\nДом построе..ый')

    @unittest.skipUnless(shutil.which('node'),'Node.js is required')
    def test_early_game_answer_survives_slow_auth_and_anonymous_is_not_recorded(self):
        script = r'''
const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
async function scenario(authorized){
 const sent=[];let resolveFirst,first=true;
 const user=authorized?{user_id:'pupil',has_required_consents:true}:null;
 const me=()=>({ok:true,json:async()=>({user})});
 const context=vm.createContext({document:{currentScript:{dataset:{game:'autumn-leaves'}}},
  location:{search:''},URLSearchParams,crypto:{randomUUID:()=> 'event-id'},
  localStorage:{setItem(){},getItem(){return null}},setInterval(){},
  fetch:async(url,options)=>{if(url==='/api/auth/me'){if(first){first=false;return await new Promise(r=>resolveFirst=()=>r(me()))}return me()}
    sent.push(JSON.parse(options.body));return{ok:true,status:200}},addEventListener(){}});
 vm.runInContext('window=globalThis',context);vm.runInContext(source,context);
 vm.runInContext('recordLearningGameAnswer(false,"ц..плёнок",new Set(["и"]),new Map([["буква","ы"]]))',context);
 assert.equal(sent.length,0);resolveFirst();
 await new Promise(r=>setTimeout(r,20));
 if(authorized){assert.equal(sent.length,1);assert.deepEqual(JSON.parse(sent[0].given_answer),['и']);assert.deepEqual(JSON.parse(sent[0].correct_answer),{буква:'ы'})}
 else assert.equal(sent.length,0);
}
(async()=>{await scenario(true);await scenario(false)})().catch(e=>{console.error(e);process.exitCode=1});
'''
        result=subprocess.run(['node','-e',script,str(server.STATIC_DIR/'game-tracker.js')],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))


if __name__ == '__main__':
    unittest.main()
