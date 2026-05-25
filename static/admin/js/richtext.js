document.addEventListener("DOMContentLoaded", () => {
  if (!window.Quill) {
    return;
  }

  const textareas = document.querySelectorAll("textarea.js-richtext");
  if (!textareas.length) return;

  textareas.forEach((textarea) => {
    if (textarea.dataset.richtextReady === "1") return;
    textarea.dataset.richtextReady = "1";

    const wrapper = document.createElement("div");
    wrapper.className = "richtext-wrapper";

    const editor = document.createElement("div");
    editor.className = "richtext-editor";
    wrapper.appendChild(editor);

    textarea.insertAdjacentElement("afterend", wrapper);

    const quill = new Quill(editor, {
      theme: "snow",
      modules: {
        toolbar: [
          [{ header: [1, 2, 3, false] }],
          ["bold", "italic", "underline", "strike"],
          [{ list: "ordered" }, { list: "bullet" }],
          [{ align: [] }],
          [{ color: [] }, { background: [] }],
          ["link", "blockquote", "code-block"],
          ["clean"],
        ],
      },
    });

    const initial = (textarea.value || "").trim();
    if (initial) {
      if (initial.includes("<") && initial.includes(">")) {
        quill.clipboard.dangerouslyPasteHTML(initial);
      } else {
        quill.setText(initial);
      }
    }

    quill.on("text-change", () => {
      textarea.value = editor.querySelector(".ql-editor").innerHTML;
    });

    textarea.style.display = "none";
  });
});
