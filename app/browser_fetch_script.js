// Cole este script no Console (F12 → Console) na página do tópico do Tibia.
// Itera sobre TODOS os .PostText e para cada um pega o container do post (td.CipPost) para autor e data.
(function() {
  const params = new URLSearchParams(window.location.search);
  const threadId = params.get('threadid');
  if (!threadId) {
    alert('Abra uma página de tópico do fórum (URL deve conter threadid=).');
    return;
  }
  const dateRe = /\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}/;

  function parsePage(doc) {
    const posts = [];
    // Estratégia: pegar TODOS os elementos com classe PostText (um por post)
    const postTextElements = doc.querySelectorAll('.PostText');
    for (const bodyEl of postTextElements) {
      // Cada .PostText está dentro de um post; subir até o container (td.CipPost ou div[id^="Post_"])
      const container = bodyEl.closest('td.CipPost') || bodyEl.closest('div[id^="Post_"]');
      if (!container) continue;
      const authorEl = container.querySelector('.PostCharacterText a[href*="subtopic=characters"][href*="name="]');
      const author = authorEl ? authorEl.textContent.trim() : '';
      const detailsEl = container.querySelector('.PostDetails');
      const detailsText = detailsEl ? detailsEl.innerText : '';
      const dateMatch = detailsText.match(dateRe);
      const dateStr = dateMatch ? dateMatch[0] : '';
      let body = bodyEl.innerText ? bodyEl.innerText : bodyEl.textContent || '';
      body = body.replace(/\s+/g, ' ').replace(/Edited by [^\n]+ on \d{2}\.\d{2}\.\d{4}[^\n]*/gi, '').trim();
      let post_id = null;
      if (container.id && String(container.id).indexOf('Post_') === 0) post_id = String(container.id).replace(/^Post_/, '');
      else { const p = container.querySelector('div[id^="Post_"]'); if (p && p.id) post_id = String(p.id).replace(/^Post_/, ''); }
      if (author && dateStr) {
        posts.push({ post_id, author, date: dateStr, body });
      }
    }
    return posts;
  }

  function getMaxPage(doc) {
    const links = doc.querySelectorAll('a[href*="pagenumber="]');
    let max = 1;
    links.forEach(a => {
      const href = (a.getAttribute && a.getAttribute('href')) || a.href || '';
      const m = href.match(/pagenumber=(\d+)/);
      if (m) max = Math.max(max, parseInt(m[1], 10));
    });
    if (max > 1) return max;
    const text = (doc.body && doc.body.innerText) || '';
    const resultsMatch = text.match(/Results:\s*(\d+)/i);
    if (resultsMatch) return Math.max(1, Math.ceil(parseInt(resultsMatch[1], 10) / 20));
    return 1;
  }

  const baseUrl = window.location.origin + window.location.pathname + '?' + new URLSearchParams({ action: 'thread', threadid: threadId }).toString();
  const maxPage = getMaxPage(document);

  (async function fetchAll() {
    let allPosts = parsePage(document);
    for (let p = 2; p <= maxPage; p++) {
      const url = baseUrl + (baseUrl.includes('?') ? '&' : '?') + 'pagenumber=' + p;
      try {
        const resp = await fetch(url);
        const html = await resp.text();
        const doc = new DOMParser().parseFromString(html, 'text/html');
        allPosts = allPosts.concat(parsePage(doc));
      } catch (e) {
        console.warn('Erro na página ' + p, e);
      }
    }
    const data = { thread_id: threadId, title: null, posts: allPosts };
    const jsonStr = JSON.stringify(data);
    try {
      await navigator.clipboard.writeText(jsonStr);
      alert('JSON copiado! (' + allPosts.length + ' posts de ' + maxPage + ' página(s)). Cole no app e clique em "Carregar e analisar".');
    } catch (e) {
      prompt('Copie o JSON abaixo (Ctrl+C):', jsonStr);
    }
  })();
})();
