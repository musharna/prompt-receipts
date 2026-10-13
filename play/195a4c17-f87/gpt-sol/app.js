const cards = document.querySelectorAll("[data-animation]");

function replay(card) {
  const icon = card.querySelector(".motion-icon");

  icon.classList.remove("is-playing");
  // Reading layout gives the browser a clean animation frame before restarting.
  void icon.offsetWidth;
  icon.classList.add("is-playing");

  if (card.dataset.animation === "favourite") {
    card.setAttribute("aria-pressed", "true");
  }
}

cards.forEach((card) => {
  card.addEventListener("click", () => replay(card));
});
