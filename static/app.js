document.querySelectorAll("[data-counter]").forEach((field) => {
  const counter = document.getElementById(field.dataset.counter);
  const updateCounter = () => {
    counter.textContent = `${field.value.length} символов`;
  };
  field.addEventListener("input", updateCounter);
  updateCounter();
});

document.querySelectorAll(".message").forEach((message) => {
  window.setTimeout(() => message.classList.add("fade"), 3600);
});
