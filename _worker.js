export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // cv.paulharvey.com.au subdomain
    if (url.hostname === 'cv.paulharvey.com.au') {
      // /docs/* → serve docx files from the main domain
      if (url.pathname.startsWith('/docs/')) {
        url.hostname = 'paulharvey.com.au';
        url.pathname = '/cv' + url.pathname;
        return Response.redirect(url.toString(), 301);
      }
      // Anything else → main site downloads anchor
      return Response.redirect('https://paulharvey.com.au/#downloads', 301);
    }

    // Main domain: /cv or /cv/ → /#downloads (page is gone, docs still served at /cv/docs/*)
    if (url.pathname === '/cv' || url.pathname === '/cv/') {
      return Response.redirect('https://paulharvey.com.au/#downloads', 301);
    }

    return env.ASSETS.fetch(request);
  }
};
