let assignmentNoticeTimer;
let assignmentSaveTimer;
const dismissedAssignmentNotices = new Set();

function attachAssignmentComposer(composer) {
  if (state.user?.role !== 'teacher' || composer.querySelector('[data-assign-composed]')) return;
  const button = document.createElement('button');
  button.type = 'button'; button.className = 'secondary-button';
  button.dataset.assignComposed = 'true'; button.textContent = 'Назначить ученикам';
  button.onclick = () => assignComposedTest(composer);
  composer.querySelector('.practice-actions').append(button);
}

async function refreshAssignmentButton() {
  const button = document.querySelector('#assignmentsButton');
  if (!button || !state.user) return;
  try {
    const data = await api('/api/assignments');
    if (!button.isConnected) return;
    button.textContent = state.user.role === 'teacher' ? 'Тесты и группы' : `Назначенные тесты${data.pending ? ` (${data.pending})` : ''}`;
    button.classList.toggle('primary-button', Boolean(data.unread));
    button.setAttribute('aria-label', data.unread ? `Новых назначенных тестов: ${data.unread}` : button.textContent);
    const newTests = (data.tests || []).filter(test => !test.seen_at && !test.completed_at && !dismissedAssignmentNotices.has(test.id));
    if (state.user.role === 'student' && newTests.length && !document.querySelector('#assignmentNotice')) {
      const notice = document.createElement('div');
      notice.id = 'assignmentNotice';
      notice.className = 'assignment-notice';
      notice.setAttribute('role', 'status');
      notice.innerHTML = `<span>Учитель назначил вам тест. Новых: ${data.unread}.</span><button class="secondary-button" type="button">Открыть тесты</button><button class="ghost-button" aria-label="Скрыть уведомление" type="button">×</button>`;
      notice.querySelector('.secondary-button').onclick = () => { notice.remove(); showAssignments(); };
      notice.querySelector('.ghost-button').onclick = () => { newTests.forEach(test => dismissedAssignmentNotices.add(test.id)); notice.remove(); };
      document.body.append(notice);
    }
  } catch (err) { console.warn('Не удалось обновить назначенные тесты', err); }
}

function learningModal(title) {
  const backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop';
  backdrop.innerHTML = `<section class="progress-modal" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}"><div class="panel-head"><h2>${escapeHtml(title)}</h2><button type="button" class="secondary-button" data-close>Закрыть</button></div><div data-content>Загрузка…</div></section>`;
  backdrop.querySelector('[data-close]').onclick = () => backdrop.remove();
  document.body.append(backdrop);
  return backdrop;
}

async function showAssignments() {
  const modal = learningModal(state.user.role === 'teacher' ? 'Тесты и группы' : 'Назначенные тесты');
  const root = modal.querySelector('[data-content]');
  try {
    const data = await api('/api/assignments');
    if (state.user.role === 'teacher') {
      root.innerHTML = `<p>Соберите вариант в тренажёре через «Составить тест», затем выберите «Назначить ученикам».</p>
        <div class="setup-grid"><label>Тренажёр<select data-activity>${Object.entries(activityMeta).filter(([id]) => /^ege(5|9|10|11|12|13|14|15)$/.test(id) || id === 'orthography-ege').map(([id, meta]) => `<option value="${id}">${escapeHtml(meta.shortTitle || meta.title)}</option>`).join('')}</select></label><button class="primary-button" data-compose>Собрать тест</button></div>
        <details><summary>Группы учеников (${data.groups.length})</summary><div data-groups></div><button class="secondary-button" data-new-group>Создать группу</button></details>
        <h3>Назначенные тесты</h3>${data.tests.map(t => `<article class="question"><h3>${escapeHtml(t.title)}</h3><p class="muted">${new Date(t.created_at).toLocaleString('ru-RU')}</p><table class="table"><tr><th>Ученик</th><th>Статус</th><th>Результат</th></tr>${t.students.map(s => `<tr><td>${escapeHtml(s.display_name)}</td><td>${s.completed_at ? 'Завершён' : s.started_at ? 'Начат' : 'Назначен'}</td><td>${s.result ? `${s.result.correct}/${s.result.total} · ${pct(s.result.correct, s.result.total)}` : '—'}</td></tr>`).join('')}</table></article>`).join('') || '<p>Назначенных тестов пока нет.</p>'}`;
      root.querySelector('[data-compose]').onclick = async () => {
        const activity = root.querySelector('[data-activity]').value;
        modal.remove();
        await loadActivity(activity);
        showTestComposer();
      };
      const groupRoot = root.querySelector('[data-groups]');
      data.groups.forEach(group => {
        const button = document.createElement('button'); button.className = 'ghost-button';
        button.textContent = `${group.title} (${group.student_ids.length}) — изменить`;
        button.onclick = () => editStudentGroup(data, group, modal);
        groupRoot.append(button);
      });
      root.querySelector('[data-new-group]').onclick = () => editStudentGroup(data, null, modal);
    } else {
      root.innerHTML = data.tests.map(t => `<article class="question"><h3>${escapeHtml(t.title)}</h3><p>Учитель: ${escapeHtml(t.teacher_name)}</p><p>${t.completed_at ? `Выполнен: ${t.result.correct}/${t.result.total}` : t.started_at ? 'Начат — можно продолжить' : 'Ожидает выполнения'}</p><button class="${t.completed_at ? 'secondary' : 'primary'}-button" data-open-test="${escapeHtml(t.id)}">${t.completed_at ? 'Результаты' : t.started_at ? 'Продолжить' : 'Начать тест'}</button></article>`).join('') || '<p>Учитель пока не назначил тесты.</p>';
      root.querySelectorAll('[data-open-test]').forEach(button => button.onclick = async () => {
        button.disabled = true;
        try { await openAssignedTest(button.dataset.openTest); modal.remove(); }
        catch (err) { button.disabled = false; alert(err.message); }
      });
    }
  } catch (err) { root.textContent = err.message; }
}

function studentCheckboxes(students, selected = []) {
  return students.map(s => `<label class="assignment-recipient"><input type="checkbox" name="student" value="${escapeHtml(s.user_id)}" ${selected.includes(s.user_id) ? 'checked' : ''}>${escapeHtml(s.display_name)}</label>`).join('') || '<p>Нет учеников, привязанных к вашему коду.</p>';
}

function editStudentGroup(data, group, parent) {
  const modal = learningModal(group ? 'Изменить группу' : 'Новая группа');
  const root = modal.querySelector('[data-content]');
  root.innerHTML = `<label>Название группы<input data-title maxlength="120" value="${escapeHtml(group?.title || '')}"></label><div class="assignment-recipients">${studentCheckboxes(data.students, group?.student_ids)}</div><p class="error"></p><button class="primary-button" data-save>Сохранить группу</button>`;
  root.querySelector('[data-save]').onclick = async () => {
    try {
      await api('/api/teacher/groups', {method:'POST',body:JSON.stringify({id:group?.id,title:root.querySelector('[data-title]').value,student_ids:[...root.querySelectorAll('[name=student]:checked')].map(i=>i.value)})});
      modal.remove(); parent.remove(); showAssignments();
    } catch (err) { root.querySelector('.error').textContent = err.message; }
  };
}

async function assignComposedTest(composer) {
  const config = {activity:state.currentActivity, mode:composer.querySelector('#testMode')?.value, count:Number(composer.querySelector('#testCount')?.value || 10), rule_ids:[...state.selectedRuleIds], include_errors:Boolean(composer.querySelector('#testIncludeErrors')?.checked)};
  if (config.activity === 'orthography-ege') {
    config.task_counts = Object.fromEntries([...composer.querySelectorAll('[data-test-orthography-count]')].map(i=>[i.dataset.testOrthographyCount,Number(i.value)]));
  }
  const modal = learningModal('Назначить тест');
  const root = modal.querySelector('[data-content]');
  try {
    const data = await api('/api/assignments');
    root.innerHTML = `<label>Название теста<input data-title maxlength="160" value="${escapeHtml(activityMeta[config.activity]?.shortTitle || activityMeta[config.activity]?.title || 'Тест')}"></label>
      <label class="assignment-recipient"><input type="checkbox" data-all>Все мои ученики (${data.students.length})</label>
      <h3>Группы</h3>${data.groups.map(g=>`<label class="assignment-recipient"><input type="checkbox" name="group" value="${escapeHtml(g.id)}">${escapeHtml(g.title)} (${g.student_ids.length})</label>`).join('') || '<p class="muted">Группы можно создать в разделе «Тесты и группы».</p>'}
      <h3>Выбрать детей</h3><div class="assignment-recipients">${studentCheckboxes(data.students)}</div><p class="error"></p><button class="primary-button" data-assign>Собрать и назначить</button>`;
    root.querySelector('[data-assign]').onclick = async (event) => {
      event.target.disabled = true;
      try {
        const result = await api('/api/assignments/create', {method:'POST',body:JSON.stringify({title:root.querySelector('[data-title]').value,config,all_students:root.querySelector('[data-all]').checked,student_ids:[...root.querySelectorAll('[name=student]:checked')].map(i=>i.value),group_ids:[...root.querySelectorAll('[name=group]:checked')].map(i=>i.value)})});
        root.innerHTML = `<p role="status">Тест из ${result.total} вопросов назначен. Учеников: ${result.recipients}.</p>`;
        composer.remove();
      } catch (err) { root.querySelector('.error').textContent = err.message; event.target.disabled = false; }
    };
  } catch (err) { root.textContent = err.message; }
}

async function openAssignedTest(id) {
  const data = await api('/api/assignments/open', {method:'POST',body:JSON.stringify({test_id:id})});
  stopTeacherStatsRefresh();
  state.currentSession = data;
  state.answers = data.answers || {};
  state.startedAt = Date.now();
  view.innerHTML = `<section class="assignment-workspace"><div class="panel-head"><h2>${escapeHtml(data.title)}</h2><button class="secondary-button" data-exit-assignment>К списку тестов</button></div><p data-assignment-save role="status"></p><div id="practiceView"></div><div id="resultView" class="hidden"></div></section>`;
  view.querySelector('[data-exit-assignment]').onclick = async () => {
    try { if (!data.result) await persistAssignedAnswers(); renderDashboard(); showAssignments(); }
    catch (err) { view.querySelector('[data-assignment-save]').textContent = err.message; }
  };
  if (data.result) renderResults(data.result); else renderQuestions();
  document.querySelector('#assignmentNotice')?.remove();
  refreshAssignmentButton();
}

async function persistAssignedAnswers() {
  const session = state.currentSession;
  if (!session?.assignment_id || session.result) return;
  await api('/api/assignments/save', {method:'POST',body:JSON.stringify({test_id:session.assignment_id,answers:state.answers})});
  const status = document.querySelector('[data-assignment-save]');
  if (status) status.textContent = 'Ответы сохранены';
}

function queueAssignedSave() {
  if (!state.currentSession?.assignment_id) return;
  clearTimeout(assignmentSaveTimer);
  assignmentSaveTimer = setTimeout(() => persistAssignedAnswers().catch(err => {
    const status = document.querySelector('[data-assignment-save]');
    if (status) status.textContent = `Не удалось сохранить ответы: ${err.message}`;
  }), 400);
}
document.addEventListener('input', event => { if (event.target.closest('#practiceView')) queueAssignedSave(); });
document.addEventListener('click', event => { if (event.target.closest('#practiceView')) queueAssignedSave(); });
