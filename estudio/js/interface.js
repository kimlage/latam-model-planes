/* Workspace layout, keyboard access and short, visible feedback. */
export function avisarUsuario (mensagem, erro = false) {
  const el = document.getElementById('notificacao');
  el.textContent = mensagem;
  el.classList.toggle('erro', erro);
  el.hidden = false;
  clearTimeout(avisarUsuario.timer);
  avisarUsuario.timer = setTimeout(() => { el.hidden = true; }, erro ? 12000 : 4500);
}

export const atalhoBloqueado = e => e.defaultPrevented ||
  !document.getElementById('modal').hidden || document.body.dataset.carregando === 'true' ||
  e.target?.isContentEditable || !!e.target?.closest('input, select, textarea') ||
  ([' ', 'Enter'].includes(e.key) && !!e.target?.closest('button, [role="button"]'));

export function ligarInterface () {
  const compacto = () => matchMedia('(max-width: 900px)').matches;
  const atualizar = () => {
    for (const id of ['lateral', 'inspetor']) {
      const aberta = compacto() ? document.body.dataset.painel === id : !document.body.classList.contains(`sem-${id}`);
      document.getElementById(`alternar-${id}`).setAttribute('aria-expanded', String(aberta));
      document.getElementById(id).inert = !aberta;
    }
  };
  for (const id of ['lateral', 'inspetor']) {
    document.getElementById(`alternar-${id}`).addEventListener('click', () => {
      if (compacto()) document.body.dataset.painel = document.body.dataset.painel === id ? '' : id;
      else document.body.classList.toggle(`sem-${id}`);
      atualizar();
    });
  }
  document.getElementById('painel-fundo').addEventListener('click', () => {
    document.body.dataset.painel = ''; atualizar();
  });
  addEventListener('resize', atualizar);
  atualizar();
  // Existing cards and rows are created dynamically. Give each one keyboard access.
  const rotular = () => {
    document.querySelectorAll('.card, .linha, .bloco h3').forEach(el => {
      if (el.hasAttribute('tabindex')) return;
      el.tabIndex = 0; el.setAttribute('role', 'button');
      el.addEventListener('keydown', e => {
        if (e.target !== el || !['Enter', ' '].includes(e.key)) return;
        e.preventDefault(); e.stopPropagation(); el.click();
      });
    });
    document.querySelectorAll('button[title]:not([aria-label])').forEach(el => {
      // Text buttons already have a name. Replacing it with a static tooltip
      // made changing labels (e.g. Record camera) invisible to assistive tools.
      if (!/[\p{L}\p{N}]/u.test(el.textContent)) el.setAttribute('aria-label', el.title);
    });
  };
  new MutationObserver(rotular).observe(document.body, { childList: true, subtree: true });
  rotular();
  document.querySelectorAll('label.tri').forEach(label => {
    const nome = label.querySelector('span').textContent;
    label.querySelectorAll('input').forEach((el, i) => el.setAttribute('aria-label', `${nome} ${'XYZ'[i]}`));
  });
}
