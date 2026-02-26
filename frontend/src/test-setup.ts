import "@testing-library/jest-dom";

// jsdom does not implement scrollIntoView — stub it globally so components
// that call element.scrollIntoView() don't throw in tests.
window.HTMLElement.prototype.scrollIntoView = function () {};
