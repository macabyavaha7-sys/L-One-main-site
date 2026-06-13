const deletedStorageKey = "l-one-motion-library-deleted";

function readDeletedCards() {
  try {
    return new Set(JSON.parse(localStorage.getItem(deletedStorageKey) || "[]"));
  } catch {
    return new Set();
  }
}

function writeDeletedCards(deletedCards) {
  localStorage.setItem(deletedStorageKey, JSON.stringify(Array.from(deletedCards)));
}

function applyDeletedCards() {
  const deletedCards = readDeletedCards();
  document.querySelectorAll(".effect-card[data-motion-id]").forEach((card) => {
    card.classList.toggle("is-hidden", deletedCards.has(card.dataset.motionId));
  });
}

function runCount(root = document) {
  root.querySelectorAll(".js-count").forEach((el) => {
    const target = Number(el.dataset.target || 0);
    const duration = 850;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = String(Math.round(target * eased)).padStart(2, "0");
      if (progress < 1) requestAnimationFrame(tick);
    }

    el.textContent = "00";
    requestAnimationFrame(tick);
  });
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch {
      // Local browser previews can expose Clipboard API while denying writes.
    }
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  textarea.style.top = "-9999px";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  if (!document.execCommand("copy")) {
    textarea.remove();
    throw new Error("Clipboard copy was rejected.");
  }
  textarea.remove();
}

function bindCopyButtons() {
  document.querySelectorAll(".code-panel").forEach((panel) => {
    const button = panel.querySelector(".copy-btn");
    if (!button) return;

    button.addEventListener("click", async () => {
      const code = panel.querySelector(".snippet-code.is-active");
      if (!code) return;
      try {
        await copyText(code.textContent);
        button.textContent = "\u5df2\u590d\u5236";
        button.classList.add("copied");
        setTimeout(() => {
          button.textContent = "\u590d\u5236\u4ee3\u7801";
          button.classList.remove("copied");
        }, 1200);
      } catch {
        button.textContent = "\u590d\u5236\u5931\u8d25";
        setTimeout(() => {
          button.textContent = "\u590d\u5236\u4ee3\u7801";
        }, 1200);
      }
    });
  });
}

function bindCodeVersionSwitches() {
  document.querySelectorAll(".code-panel").forEach((panel) => {
    const buttons = panel.querySelectorAll("[data-code-select]");
    const codeBlocks = panel.querySelectorAll("[data-code-version]");
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const version = button.dataset.codeSelect;
        buttons.forEach((item) => item.classList.toggle("is-active", item === button));
        codeBlocks.forEach((code) => {
          const active = code.dataset.codeVersion === version;
          code.classList.toggle("is-active", active);
          code.closest("pre").hidden = !active;
        });
      });
    });
  });
}

function bindDeleteButtons() {
  document.querySelectorAll(".effect-card[data-motion-id]").forEach((card) => {
    const button = card.querySelector(".delete-card");
    if (!button) return;

    button.addEventListener("click", () => {
      const deletedCards = readDeletedCards();
      deletedCards.add(card.dataset.motionId);
      writeDeletedCards(deletedCards);
      card.classList.add("is-hidden");
    });
  });

}

applyDeletedCards();
runCount();
setInterval(() => runCount(), 2600);
bindCopyButtons();
bindCodeVersionSwitches();
bindDeleteButtons();
