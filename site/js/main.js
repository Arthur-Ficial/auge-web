// Minimal JS — just the copy buttons.
document.addEventListener("click", function (e) {
  const btn = e.target.closest(".copy-btn");
  if (!btn) return;
  const target = btn.previousElementSibling;
  if (!target) return;
  const text = target.innerText.trim();
  const orig = btn.textContent;
  navigator.clipboard.writeText(text).then(
    function () {
      btn.textContent = "copied";
      btn.classList.add("copied");
      setTimeout(function () {
        btn.textContent = orig;
        btn.classList.remove("copied");
      }, 1400);
    },
    function () {
      btn.textContent = "copy failed";
      setTimeout(function () { btn.textContent = orig; }, 1400);
    }
  );
});
