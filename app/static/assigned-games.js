/* Assigned games keep their own access grants and reuse pupil work lists. */
async function chooseOwnedGameAssignment() {
  const modal=learningModal('Назначить игру из моего комплекта');
  const root=modal.querySelector('[data-content]');
  root.textContent='Загрузка игр…';
  try {
    const data=await api('/api/teacher/games');
    if (!modal.isConnected) return;
    const games=(data.purchased || []).filter(game=>game.can_assign);
    root.innerHTML='<p>Выберите купленную или подаренную игру. Ученики получат полную версию в списке назначенных работ.</p>'+
      (games.map((game,index)=>'<article class="question"><p class="eyebrow">'+(game.kind==='gifted'?'Подаренная игра':'Купленная игра')+'</p><h3>'+escapeHtml(game.title)+'</h3><button class="primary-button" data-select-owned-game="'+index+'">Выбрать учеников</button></article>').join('') || '<p>В вашем комплекте пока нет купленных или подаренных игр с онлайн-версией.</p>');
    root.querySelectorAll('[data-select-owned-game]').forEach(button=>button.onclick=()=>{
      const game=games[Number(button.dataset.selectOwnedGame)];
      modal.remove();assignTeacherGame(game);
    });
  } catch(err) {if(root.isConnected)root.textContent=err.message;}
}

async function assignTeacherGame(game) {
  const modal=learningModal('Назначить игру ученикам');
  const root=modal.querySelector('[data-content]');
  try {
    const data=await api('/api/assignments');
    root.innerHTML=`<h3>${escapeHtml(game.title)}</h3><p>${game.public_id ? 'Ученикам будет доступен этот игровой набор.' : 'Ученикам будет доступна полная версия игры из вашего кабинета.'}</p>${deadlineFields()}<label>Ответов для выполнения<input type="number" min="0" max="500" value="0" data-game-target></label><p class="muted">0 — свободный доступ без нормы. Для игр с проверкой ответов можно указать нужное количество решений.</p><label class="assignment-recipient"><input type="checkbox" data-all>Все мои ученики (${data.students.length})</label><h3>Группы</h3>${data.groups.map(g=>`<label class="assignment-recipient"><input type="checkbox" name="group" value="${escapeHtml(g.id)}">${escapeHtml(g.title)}</label>`).join('')||'<p class="muted">Группы пока не созданы.</p>'}<h3>Выбрать учеников</h3><div class="assignment-recipients">${studentCheckboxes(data.students)}</div><p class="error" role="alert"></p><button class="primary-button" data-assign-game>Назначить игру</button>`;
    root.querySelector('[data-assign-game]').onclick=async event=>{
      event.target.disabled=true;
      try {
        const result=await api('/api/assigned-games/create',{method:'POST',body:JSON.stringify({slug:game.slug,public_id:game.public_id,
          due_at:dueFrom(root),target_count:Number(root.querySelector('[data-game-target]').value),
          all_students:root.querySelector('[data-all]').checked,student_ids:[...root.querySelectorAll('[name=student]:checked')].map(i=>i.value),
          group_ids:[...root.querySelectorAll('[name=group]:checked')].map(i=>i.value)})});
        root.innerHTML=`<p role="status">Игра появилась в кабинетах учеников в списке назначенных тестов и игр. Получателей: ${result.recipients}.</p>`;
      } catch(err){root.querySelector('.error').textContent=err.message;event.target.disabled=false;}
    };
  } catch(err){root.textContent=err.message;}
}

function assignedGameCard(game) {
  const teacher=state.user.role==='teacher';
  const status=game.revoked_at?'Доступ отозван':game.completed_at?'Выполнено':game.overdue?'Просрочено · можно играть':game.started_at?'Начата':'Назначена';
  return `<article class="question assigned-game-card"><p class="eyebrow">${game.kind==='full'?'Полная версия игры':'Игровой набор'}</p><h3>${escapeHtml(game.title)}</h3>${teacher?`<button class="ghost-button" data-open-student-card="${escapeHtml(game.student_id)}">${escapeHtml(game.display_name)}</button>`:''}<p>${deadlineHtml(game)}</p><p>${status}</p><p>Решено: ${game.checked}${game.target_count?' из '+game.target_count:''} · верно: ${game.correct}${game.checked?' · точность: '+pct(game.correct,game.checked):''}</p>${game.target_count?`<progress value="${Math.min(game.checked,game.target_count)}" max="${game.target_count}" aria-label="Выполнение игры"></progress>`:'<p class="muted">Свободный доступ без нормы ответов</p>'}<div class="practice-actions">${!game.revoked_at?`<button class="primary-button" data-launch-assigned-game="${escapeHtml(game.id)}">${teacher?'Открыть игру':'Играть'}</button>`:''}${teacher?`<button class="ghost-button" data-game-deadline="${escapeHtml(game.id)}" data-student="${escapeHtml(game.student_id)}" data-due="${escapeHtml(game.due_at||'')}">Изменить срок</button>${!game.revoked_at?`<button class="ghost-button" data-revoke-assigned-game="${escapeHtml(game.id)}" data-student="${escapeHtml(game.student_id)}">Отозвать игру</button>`:''}`:''}</div><p class="error" role="alert" data-game-error></p></article>`;
}

function bindAssignedGames(root,refresh) {
  root.querySelectorAll('[data-launch-assigned-game]').forEach(b=>b.onclick=async()=>{
    b.disabled=true;
    try {
      await leaveAssignedWorkspace();
      const data=await api('/api/assigned-games/open',{method:'POST',body:JSON.stringify({game_id:b.dataset.launchAssignedGame})});
      location.assign(data.url);
    } catch(err){b.disabled=false;b.closest('article').querySelector('[data-game-error]').textContent=err.message;}
  });
  root.querySelectorAll('[data-game-deadline]').forEach(b=>b.onclick=()=>editAssignmentDeadline(b.dataset.gameDeadline,b.dataset.student,b.dataset.due,refresh,'game'));
  root.querySelectorAll('[data-revoke-assigned-game]').forEach(b=>b.onclick=async()=>{
    if(!confirm('Отозвать доступ к игре у этого ученика? Решения останутся в статистике.'))return;
    b.disabled=true;
    try {await api('/api/assigned-games/update',{method:'POST',body:JSON.stringify({game_id:b.dataset.revokeAssignedGame,student_id:b.dataset.student,revoke:true})});await refresh();}
    catch(err){b.disabled=false;b.closest('article').querySelector('[data-game-error]').textContent=err.message;}
  });
}
