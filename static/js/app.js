(function () {
  "use strict";

  // ---- جستجوی زنده ----
  var form = document.querySelector("[data-live-search]");
  if (form) {
    var input = form.querySelector("input[name=q]");
    var box = document.getElementById("results");
    var url = form.getAttribute("data-live-search");
    var timer = null;
    var counter = 0;

    var run = function () {
      var q = input.value.trim();
      var mine = ++counter;
      history.replaceState(null, "", q ? url + "?q=" + encodeURIComponent(q) : url);
      fetch(url + "?partial=1&q=" + encodeURIComponent(q), { credentials: "same-origin" })
        .then(function (r) {
          if (r.redirected || !r.ok) { window.location.reload(); return null; }
          return r.text();
        })
        .then(function (html) {
          if (html !== null && mine === counter) { box.innerHTML = html; }
        })
        .catch(function () {
          if (mine === counter) {
            box.innerHTML = '<p class="msg error">ارتباط با برنامه برقرار نشد. مطمئن شوید Findent در حال اجراست.</p>';
          }
        });
    };

    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(run, 200);
    });

    // Enter: اولین پرونده‌ی نتیجه را باز کن
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      clearTimeout(timer);
      var first = box.querySelector(".result .open");
      if (first) { window.location.href = first.getAttribute("href"); } else { run(); }
    });

    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
  }

  // ---- تأیید قبل از ارسال و جلوگیری از ثبت دوباره با دوبار کلیک ----
  document.addEventListener("submit", function (e) {
    var f = e.target;
    if (e.defaultPrevented) { return; }
    var msg = f.getAttribute("data-confirm");
    if (msg && !window.confirm(msg)) {
      e.preventDefault();
      return;
    }
    var buttons = f.querySelectorAll("button[type=submit]");
    setTimeout(function () {
      buttons.forEach(function (b) { b.disabled = true; });
    }, 0);
  });

  // بازگشت با دکمه‌ی Back مرورگر: دکمه‌ها دوباره فعال شوند
  window.addEventListener("pageshow", function () {
    document.querySelectorAll("button[type=submit]").forEach(function (b) { b.disabled = false; });
  });
})();
