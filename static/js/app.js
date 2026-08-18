document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".toast").forEach((toast, index) => {
    setTimeout(() => toast.classList.add("toast-show"), 20 + index * 80);

    const dismiss = () => {
      toast.classList.remove("toast-show");
      setTimeout(() => toast.remove(), 250);
    };
    const timer = setTimeout(dismiss, 4000);
    toast.addEventListener("click", () => {
      clearTimeout(timer);
      dismiss();
    });
  });

  const radios = document.querySelectorAll('input[name="selecionado"]');
  const btnEdit = document.getElementById("btn-edit");
  const btnDelete = document.getElementById("btn-delete");
  const btnHistorico = document.getElementById("btn-historico");
  const deleteForm = document.getElementById("delete-form");

  if (!radios.length) return;

  function setSelected(id) {
    document.querySelectorAll("table.data tbody tr").forEach((tr) => {
      tr.classList.toggle("selected", tr.dataset.id === String(id));
    });

    if (btnEdit) {
      btnEdit.href = `/equipamentos/${id}/editar`;
      btnEdit.removeAttribute("aria-disabled");
    }
    if (btnDelete) {
      btnDelete.dataset.id = id;
      btnDelete.removeAttribute("aria-disabled");
    }
    if (btnHistorico) {
      btnHistorico.href = `/equipamentos/${id}/historico`;
      btnHistorico.removeAttribute("aria-disabled");
    }
  }

  radios.forEach((radio) => {
    radio.addEventListener("change", () => setSelected(radio.value));
  });

  document.querySelectorAll("table.data tbody tr").forEach((tr) => {
    tr.addEventListener("click", (event) => {
      if (event.target.tagName === "INPUT") return;
      const radio = tr.querySelector('input[name="selecionado"]');
      if (radio) {
        radio.checked = true;
        setSelected(radio.value);
      }
    });
  });

  if (btnDelete) {
    btnDelete.addEventListener("click", () => {
      const id = btnDelete.dataset.id;
      if (!id) return;
      if (!confirm("Excluir este equipamento? Esta ação não pode ser desfeita.")) return;
      deleteForm.action = `/equipamentos/${id}/excluir`;
      deleteForm.submit();
    });
  }
});
