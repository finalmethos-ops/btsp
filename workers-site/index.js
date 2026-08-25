addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  // Minimal worker to satisfy Wrangler entrypoint during builds.
  // For production please replace with the real worker logic or let Wrangler generate the worker entrypoint when using a framework integration.
  return new Response('<!doctype html><html><body><h1>PEM Buddys - placeholder worker</h1></body></html>', {
    headers: { 'content-type': 'text/html;charset=UTF-8' },
  });
}
