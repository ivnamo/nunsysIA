(function () {
  const DRAG_ACTIVE_CLASS = "chainlit-pdf-drag-active";

  function decodePreviewPayload(value) {
    const normalized = value.trim().replace(/-/g, "+").replace(/_/g, "/");
    const padding = normalized.length % 4 === 0 ? "" : "=".repeat(4 - (normalized.length % 4));
    const binary = window.atob(normalized + padding);
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes));
  }

  function hasPreviewShape(value) {
    if (Array.isArray(value)) {
      return value.some(hasPreviewShape);
    }
    return Boolean(value && value.chunk_id && value.text_preview);
  }

  function encodedCandidates(text) {
    return (text || "")
      .split(/\s+/)
      .map((item) => item.trim())
      .filter((item) => item.length > 40 && /^[A-Za-z0-9_-]+={0,2}$/.test(item));
  }

  function hideNode(node) {
    node.hidden = true;
    node.style.display = "none";
  }

  function hideLegacyPayloadNode(node) {
    const container = node.closest("pre") || node;
    hideNode(container);

    const parent = container.parentElement;
    if (!parent) {
      return;
    }

    Array.from(parent.children).forEach((child) => {
      if (child !== container && /^rag(?:-citation-previews)?$/i.test((child.textContent || "").trim())) {
        hideNode(child);
      }
    });
  }

  function hideLegacyCitationPayloads() {
    document.querySelectorAll("code, pre").forEach((node) => {
      encodedCandidates(node.textContent || "").forEach((candidate) => {
        try {
          if (hasPreviewShape(decodePreviewPayload(candidate))) {
            hideLegacyPayloadNode(node);
          }
        } catch {
          // Ignore ordinary code blocks and non-preview text.
        }
      });
    });
  }

  function hasDraggedFiles(event) {
    return Array.from(event.dataTransfer?.types || []).includes("Files");
  }

  function setupDocumentDragState() {
    let dragDepth = 0;

    function showDragState() {
      document.body.classList.add(DRAG_ACTIVE_CLASS);
    }

    function clearDragState() {
      dragDepth = 0;
      document.body.classList.remove(DRAG_ACTIVE_CLASS);
    }

    window.addEventListener("dragenter", (event) => {
      if (!hasDraggedFiles(event)) {
        return;
      }
      dragDepth += 1;
      showDragState();
    });

    window.addEventListener("dragover", (event) => {
      if (hasDraggedFiles(event)) {
        showDragState();
      }
    });

    window.addEventListener("dragleave", (event) => {
      if (!hasDraggedFiles(event)) {
        return;
      }
      dragDepth = Math.max(0, dragDepth - 1);
      if (dragDepth === 0) {
        clearDragState();
      }
    });

    window.addEventListener("drop", clearDragState, true);
    window.addEventListener("dragend", clearDragState, true);
  }

  function init() {
    hideLegacyCitationPayloads();
    setupDocumentDragState();

    const observer = new MutationObserver(() => {
      window.requestAnimationFrame(hideLegacyCitationPayloads);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
