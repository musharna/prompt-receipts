document.querySelectorAll('[data-replay]').forEach((button) => {
  button.addEventListener('click', () => {
    const stage = document.getElementById(button.dataset.replay);
    // Replacing the stage contents gives every animation a clean timeline.
    stage.replaceChildren(...[...stage.children].map((child) => child.cloneNode(true)));
  });
});
