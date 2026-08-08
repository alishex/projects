(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var terminalTimer = null;

  function getStoredLang() {
    var stored = null;
    try {
      stored = localStorage.getItem("lang");
    } catch (e) {}
    return stored === "en" || stored === "ru" || stored === "uz" ? stored : "en";
  }

  function setStoredLang(lang) {
    try {
      localStorage.setItem("lang", lang);
    } catch (e) {}
  }

  function applyTranslations(lang) {
    document.documentElement.setAttribute("lang", lang);

    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      var val = window.I18N.t(key, lang);
      if (val == null) return;
      if (el.hasAttribute("data-i18n-html")) {
        el.innerHTML = val;
      } else {
        el.textContent = val;
      }
    });

    document.querySelectorAll("[data-i18n-attr]").forEach(function (el) {
      var spec = el.getAttribute("data-i18n-attr");
      var sep = spec.indexOf(":");
      if (sep === -1) return;
      var attr = spec.slice(0, sep);
      var key = spec.slice(sep + 1);
      var val = window.I18N.t(key, lang);
      if (val != null) el.setAttribute(attr, val);
    });
  }

  function paintLangButtons(lang) {
    document.querySelectorAll("[data-lang]").forEach(function (btn) {
      var isActive = btn.getAttribute("data-lang") === lang;
      btn.classList.toggle("is-active", isActive);
      btn.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  }

  function initLang() {
    var lang = getStoredLang();
    applyTranslations(lang);
    paintLangButtons(lang);
    renderTerminal(lang, true);

    document.querySelectorAll("[data-lang]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var next = btn.getAttribute("data-lang");
        if (next === document.documentElement.getAttribute("lang")) return;
        applyTranslations(next);
        paintLangButtons(next);
        setStoredLang(next);
        renderTerminal(next, false);
      });
    });
  }

  function initBoot() {
    var overlay = document.getElementById("boot");
    if (!overlay) return;

    var alreadyShown = false;
    try {
      alreadyShown = sessionStorage.getItem("bootShown") === "1";
    } catch (e) {}

    if (reduceMotion || alreadyShown) {
      overlay.remove();
      return;
    }

    var lang = document.documentElement.getAttribute("lang") || "en";
    var lines = (window.I18N && window.I18N.boot && window.I18N.boot[lang]) || [];
    var linesEl = overlay.querySelector("[data-boot-lines]");
    var fillEl = overlay.querySelector("[data-boot-fill]");
    var done = false;

    function finish() {
      if (done) return;
      done = true;
      try {
        sessionStorage.setItem("bootShown", "1");
      } catch (e) {}
      overlay.classList.add("is-hidden");
      window.removeEventListener("keydown", finish);
      window.removeEventListener("pointerdown", finish);
      setTimeout(function () {
        overlay.remove();
      }, 500);
    }

    window.addEventListener("keydown", finish);
    window.addEventListener("pointerdown", finish);
    setTimeout(finish, 3500);

    if (!lines.length || !linesEl || !fillEl) {
      finish();
      return;
    }

    var i = 0;
    function nextLine() {
      if (done) return;
      if (i >= lines.length) {
        fillEl.style.width = "100%";
        setTimeout(finish, 350);
        return;
      }
      var isLast = i === lines.length - 1;
      var row = document.createElement("div");
      row.className = "line" + (isLast ? " ok" : "");
      row.innerHTML =
        "<span>" + (isLast ? "✓" : "&gt;") + "</span><span>" + lines[i] + "</span>";
      linesEl.appendChild(row);
      fillEl.style.width = Math.round(((i + 1) / lines.length) * 100) + "%";
      i++;
      setTimeout(nextLine, 260);
    }

    setTimeout(nextLine, 150);
  }

  function initReveal() {
    var items = document.querySelectorAll(".reveal");
    if (reduceMotion || !("IntersectionObserver" in window)) {
      items.forEach(function (el) {
        el.classList.add("is-visible");
      });
      return;
    }
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
    );
    items.forEach(function (el) {
      io.observe(el);
    });
  }

  function renderTerminal(lang, animate) {
    var body = document.querySelector("[data-terminal-body]");
    if (!body) return;

    if (terminalTimer) {
      clearTimeout(terminalTimer);
      terminalTimer = null;
    }

    var script = (window.I18N.terminal && window.I18N.terminal[lang]) || [];
    body.innerHTML = "";

    if (reduceMotion || !animate) {
      body.innerHTML = script
        .map(function (l) {
          return (
            '<div class="line prompt">' + l.prompt + "</div>" +
            '<div class="line out">' + l.out + "</div>"
          );
        })
        .join("") + '<span class="cursor" aria-hidden="true"></span>';
      return;
    }

    var lineIndex = 0;
    var charIndex = 0;
    var typingPrompt = true;
    var currentLineEl = null;

    function step() {
      if (lineIndex >= script.length) {
        var cursor = document.createElement("span");
        cursor.className = "cursor";
        cursor.setAttribute("aria-hidden", "true");
        body.appendChild(cursor);
        return;
      }

      var entry = script[lineIndex];
      var text = typingPrompt ? entry.prompt : entry.out;

      if (charIndex === 0) {
        currentLineEl = document.createElement("div");
        currentLineEl.className = "line " + (typingPrompt ? "prompt" : "out");
        body.appendChild(currentLineEl);
      }

      charIndex++;
      currentLineEl.textContent = text.slice(0, charIndex);

      if (charIndex >= text.length) {
        charIndex = 0;
        if (typingPrompt) {
          typingPrompt = false;
          terminalTimer = setTimeout(step, 260);
        } else {
          typingPrompt = true;
          lineIndex++;
          terminalTimer = setTimeout(step, 420);
        }
      } else {
        terminalTimer = setTimeout(step, 24 + Math.random() * 26);
      }
    }

    step();
  }

  function initNetGraph() {
    var canvas = document.querySelector("[data-net-graph]");
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext("2d");
    var wrap = canvas.parentElement;
    var nodes = [];
    var mouse = { x: -9999, y: -9999, active: false };
    var W = 0,
      H = 0,
      dpr = Math.max(1, window.devicePixelRatio || 1);

    function resize() {
      W = wrap.clientWidth;
      H = wrap.clientHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      canvas.style.width = W + "px";
      canvas.style.height = H + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var count = Math.max(9, Math.min(20, Math.round((W * H) / 26000)));
      nodes = [];
      for (var i = 0; i < count; i++) {
        nodes.push({
          x: Math.random() * W,
          y: Math.random() * H,
          vx: (Math.random() - 0.5) * 0.18,
          vy: (Math.random() - 0.5) * 0.18,
          r: 1.4 + Math.random() * 1.6
        });
      }
    }

    var styles = getComputedStyle(document.documentElement);

    function colors() {
      styles = getComputedStyle(document.documentElement);
      return {
        edge: styles.getPropertyValue("--edge").trim() || "rgba(255,90,31,0.2)",
        node: styles.getPropertyValue("--node").trim() || "rgba(233,235,242,0.5)"
      };
    }

    function draw() {
      var c = colors();
      ctx.clearRect(0, 0, W, H);
      for (var i = 0; i < nodes.length; i++) {
        for (var j = i + 1; j < nodes.length; j++) {
          var a = nodes[i],
            b = nodes[j];
          var dx = a.x - b.x,
            dy = a.y - b.y;
          var d = Math.sqrt(dx * dx + dy * dy);
          var max = Math.min(W, H) * 0.32;
          if (d < max) {
            ctx.globalAlpha = 1 - d / max;
            ctx.strokeStyle = c.edge;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }
      if (mouse.active) {
        var reach = Math.min(W, H) * 0.38;
        for (var k = 0; k < nodes.length; k++) {
          var node = nodes[k];
          var mdx = node.x - mouse.x,
            mdy = node.y - mouse.y;
          var md = Math.sqrt(mdx * mdx + mdy * mdy);
          if (md < reach) {
            ctx.globalAlpha = (1 - md / reach) * 0.9;
            ctx.strokeStyle = c.edge;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(node.x, node.y);
            ctx.lineTo(mouse.x, mouse.y);
            ctx.stroke();
          }
        }
        ctx.globalAlpha = 0.9;
        ctx.fillStyle = c.node;
        ctx.beginPath();
        ctx.arc(mouse.x, mouse.y, 2.6, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.globalAlpha = 1;
      ctx.fillStyle = c.node;
      nodes.forEach(function (n) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    function tick() {
      nodes.forEach(function (n) {
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 0 || n.x > W) n.vx *= -1;
        if (n.y < 0 || n.y > H) n.vy *= -1;
      });
      draw();
      raf = requestAnimationFrame(tick);
    }

    var raf;
    resize();
    draw();
    if (!reduceMotion) {
      raf = requestAnimationFrame(tick);
    }

    var resizeTimer;
    window.addEventListener("resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        resize();
        draw();
      }, 150);
    });

    if (!reduceMotion && window.matchMedia("(pointer: fine)").matches) {
      var hero = canvas.closest(".hero") || wrap;
      hero.addEventListener("pointermove", function (e) {
        var rect = wrap.getBoundingClientRect();
        mouse.x = e.clientX - rect.left;
        mouse.y = e.clientY - rect.top;
        mouse.active = true;
      });
      hero.addEventListener("pointerleave", function () {
        mouse.active = false;
      });
    }
  }

  function initScrollProgress() {
    var fill = document.querySelector("[data-scroll-fill]");
    if (!fill) return;
    var ticking = false;
    function update() {
      var doc = document.documentElement;
      var scrollable = doc.scrollHeight - doc.clientHeight;
      var pct = scrollable > 0 ? (doc.scrollTop / scrollable) * 100 : 0;
      fill.style.width = pct + "%";
      ticking = false;
    }
    window.addEventListener(
      "scroll",
      function () {
        if (!ticking) {
          requestAnimationFrame(update);
          ticking = true;
        }
      },
      { passive: true }
    );
    update();
  }

  function initYear() {
    var el = document.querySelector("[data-year]");
    if (el) el.textContent = "2026";
  }

  /* ---- real logo as a standalone floating 3D object — entrance animation +
     continuous idle motion + pointer-follow tilt. Pure CSS 3D transform, no canvas. ---- */
  function initBrandMark3D() {
    var mark = document.querySelector("[data-brand-mark]");
    if (!mark || reduceMotion) return;

    var idle = { x: 6, y: -10 };
    var t0 = performance.now();
    var pointerActive = false;
    var pointerTilt = { x: 0, y: 0 };

    function idleAngle() {
      var t = (performance.now() - t0) / 1000;
      return {
        x: Math.sin(t * 0.55) * idle.x,
        y: Math.cos(t * 0.4) * idle.y
      };
    }

    function apply() {
      var base = pointerActive ? pointerTilt : idleAngle();
      mark.style.transform = "rotateX(" + base.x + "deg) rotateY(" + base.y + "deg)";
      requestAnimationFrame(apply);
    }
    requestAnimationFrame(apply);

    if (window.matchMedia("(pointer: fine)").matches) {
      var dock = mark.closest(".brand-mark-dock");
      dock.addEventListener("pointermove", function (e) {
        var r = dock.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - 0.5;
        var py = (e.clientY - r.top) / r.height - 0.5;
        pointerTilt = { x: -py * 34, y: px * 34 };
        pointerActive = true;
      });
      dock.addEventListener("pointerleave", function () { pointerActive = false; });
    }
  }

  /* ---- subtle 3D pointer-tilt on cards ---- */
  function initCardTilt() {
    if (reduceMotion || !window.matchMedia("(pointer: fine)").matches) return;
    var cards = document.querySelectorAll(".tilt-card");
    var MAX = 5;
    cards.forEach(function (card) {
      card.addEventListener("pointermove", function (e) {
        var r = card.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - 0.5;
        var py = (e.clientY - r.top) / r.height - 0.5;
        card.style.transition = "transform 0.05s linear";
        card.style.transform = "perspective(900px) rotateX(" + (-py * MAX * 2) + "deg) rotateY(" + (px * MAX * 2) + "deg) translateZ(2px)";
      });
      card.addEventListener("pointerleave", function () {
        card.style.transition = "transform 0.5s cubic-bezier(.16,.84,.44,1)";
        card.style.transform = "perspective(900px) rotateX(0deg) rotateY(0deg)";
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initLang();
    initBoot();
    initReveal();
    initNetGraph();
    initBrandMark3D();
    initCardTilt();
    initScrollProgress();
    initYear();
  });
})();
