document.querySelectorAll('[data-nav]').forEach(link => {
  const current = window.location.pathname.split('/').pop() || 'index.html'
  if (link.getAttribute('href') === current) {
    link.classList.add('is-active')
  }
})

document.querySelectorAll('[data-summary-toggle]').forEach(button => {
  const targetSelector = button.getAttribute('data-summary-toggle')
  const target = targetSelector ? document.querySelector(targetSelector) : null

  if (!target) return

  button.addEventListener('click', () => {
    const expanded = target.getAttribute('data-expanded') === 'true'
    target.setAttribute('data-expanded', String(!expanded))

    const collapsed = target.getAttribute('data-collapsed')
    const full = target.getAttribute('data-full')
    if (!collapsed || !full) return

    target.textContent = expanded ? collapsed : full
    button.textContent = expanded ? '展开原文' : '收起原文'
  })
})
