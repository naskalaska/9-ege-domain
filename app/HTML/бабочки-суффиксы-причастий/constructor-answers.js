"use strict";

checkAnswer = function checkConstructorAnswer() {
  const card = document.querySelector(".taskCard");
  const input = card?.querySelector(".letterInput");
  const host = card?.querySelector(".feedbackHost");
  const button = card?.querySelector("[data-check]");
  if (!card || !input || !host || current === null) return;
  const normalize = (value) => String(value || "").trim().toLowerCase().replace(/ё/g, "е");
  const value = normalize(input.value);
  const answer = normalize(items[current].answer);
  if (!value) {
    input.focus();
    input.classList.add("invalid");
    return;
  }
  input.classList.remove("invalid");
  if (value === answer) {
    const images = ["orange-monarch.png", "blue-morpho.png", "yellow-swallowtail.png", "purple-emperor.png", "pink-fantasy.png", "zebra-longwing.png"];
    done.add(current);
    card.classList.remove("bad");
    card.classList.add("good");
    button.disabled = true;
    input.disabled = true;
    card.querySelector(".modalPod").insertAdjacentHTML("beforeend", `<span class="release"><img src="${asset(images[current % images.length])}" alt="Бабочка вылетает из кокона"></span>`);
    host.innerHTML = `<div class="feedback good"><b>Бабочка свободна!</b><span>${esc(items[current].correct_spelling || `Верный ответ: ${items[current].answer}`)}. ${esc(items[current].explanation || "")}</span></div>`;
    setTimeout(() => { current = null; render(); }, 1800);
    return;
  }
  card.classList.remove("good");
  card.classList.add("bad");
  const pod = card.querySelector(".modalPod");
  if (!pod.querySelector(".caterpillar")) pod.insertAdjacentHTML("beforeend", `<span class="caterpillar"><img src="${asset("grumpy-caterpillar.png")}" alt="Недовольная гусеница"></span>`);
  host.innerHTML = '<div class="feedback bad"><b>Гусеница проснулась</b><span>Пока неверно. Проверьте правило и попробуйте ещё раз — ответ не показан.</span></div>';
  input.select();
};
