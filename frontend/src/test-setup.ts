import "@testing-library/jest-dom";

// jsdom does not implement scrollIntoView — stub it globally so components
// that call element.scrollIntoView() don't throw in tests.
window.HTMLElement.prototype.scrollIntoView = function () {};

// Stub requestAnimationFrame to be synchronous in tests so RAF-throttled
// store actions (e.g. appendStreamingContent) flush immediately.
window.requestAnimationFrame = (fn: FrameRequestCallback): number => {
  fn(performance.now());
  return 0;
};
window.cancelAnimationFrame = (_id: number): void => {};
