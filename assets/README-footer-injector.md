assets/footer.html — unified footer template
assets/footer.css — minimal footer styles
assets/footer.js  — injector script (replaces existing <footer> elements with unified footer)

How to enable on pages:
- Add before </body> on each HTML page:
  <script src="/assets/footer.js" defer></script>

Notes:
- The injector replaces any existing <footer> elements in-place so you don't have to manually remove them.
- fetch('/assets/footer.html') requires a web server (file:// will not work).
