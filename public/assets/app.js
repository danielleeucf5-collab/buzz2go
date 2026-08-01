const chips = document.querySelectorAll('[data-category]');
const cards = document.querySelectorAll('[data-card]');

chips.forEach((chip) => {
  chip.addEventListener('click', () => {
    chips.forEach((c) => c.classList.remove('active'));
    chip.classList.add('active');
    const selected = chip.dataset.category;

    cards.forEach((card) => {
      const visible = selected === '전체' || card.dataset.card === selected;
      card.style.display = visible ? 'flex' : 'none';
    });
  });
});
