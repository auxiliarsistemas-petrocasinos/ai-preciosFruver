const form = document.querySelector("[data-purchase-need-form]");
const quantityInput = document.querySelector("#quantity");
const quantityError = "Ingrese una cantidad numérica mayor que cero.";

function validateQuantity() {
  if (!quantityInput.value) {
    quantityInput.setCustomValidity("");
    return;
  }

  const significand = quantityInput.value.split(/[eE]/, 1)[0].replace(/[+.]/g, "");
  quantityInput.setCustomValidity(/^[^-]*[1-9]/.test(significand) ? "" : quantityError);
}

if (form && quantityInput) {
  quantityInput.addEventListener("input", validateQuantity);
  form.addEventListener("submit", (event) => {
    validateQuantity();
    if (!quantityInput.checkValidity()) {
      event.preventDefault();
      quantityInput.reportValidity();
    }
  });
}
