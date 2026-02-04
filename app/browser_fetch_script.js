// Cole este script no Console (F12 → Console) enquanto estiver na página do tópico do Tibia.
// Ele baixa todas as páginas do tópico e copia o JSON para a área de transferência.
(function() {
  const params = new URLSearchParams(window.location.search);
  const threadId = params.get('threadid');
  if (!threadId) {
    alert('Abra uma página de tópico do fórum (URL deve conter threadid=).');
    return;
  }
  const dateRe = /\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}/g;
  const postIdRe = /Post\s*#(\d+)/i;
  const SKIP_NAMES = /^(community|tibia|forum|board jump|thread jump|post jump|page jump|choose board|section)$/i;

  function parsePage(doc) {
    const posts = [];
    const seen = new Set();
    const links = doc.querySelectorAll('a[href*="subtopic=characters"][href*="name="]');
    for (const a of links) {
      const author = (a.textContent || '').trim();
      if (!author || author.length > 50) continue;
      if (SKIP_NAMES.test(author)) continue;
      // Menor ancestral que contém data + nome do autor (bloco de um único post)
      let el = a.parentElement;
      let best = null;
      let bestEl = null;
      let bestLen = Infinity;
      for (let i = 0; i < 25 && el; i++) {
        const text = (el.innerText || '').replace(/\s+/g, ' ');
        const dates = text.match(dateRe);
        const hasAuthor = text.indexOf(author) !== -1;
        if (dates && dates.length >= 1 && hasAuthor && text.length < bestLen && text.length > 30) {
          bestLen = text.length;
          best = text;
          bestEl = el;
        }
        el = el.parentElement;
      }
      if (!best || !bestEl) continue;
      // Só aceitar se este link for o primeiro link de personagem do bloco (evita links no corpo do post)
      const firstCharLink = bestEl.querySelector('a[href*="subtopic=characters"][href*="name="]');
      if (firstCharLink !== a) continue;
      const dateMatch = best.match(/\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}/);
      const dateStr = dateMatch ? dateMatch[0] : '';
      const key = author + '|' + dateStr;
      if (seen.has(key)) continue;
      seen.add(key);
      let body = best.replace(dateStr, '').replace(/Edited by [^\n]+ on \d{2}\.\d{2}\.\d{4}[^\n]*/gi, '').replace(/_+/g, '').replace(/\s+/g, ' ').trim();
      const postIdMatch = best.match(postIdRe);
      posts.push({ post_id: postIdMatch ? postIdMatch[1] : null, author, date: dateStr, body });
    }
    return posts;
  }

  function getMaxPage(doc) {
    const pageLinks = Array.from(doc.querySelectorAll('a[href*="pagenumber="]'));
    const pageNumbers = pageLinks.map(a => {
      const href = a.getAttribute('href') || a.href || '';
      const m = href.match(/pagenumber=(\d+)/);
      return m ? parseInt(m[1], 10) : null;
    }).filter(Boolean);
    if (pageNumbers.length > 0) return Math.max(...pageNumbers);
    // Fallback: "Results: 206" -> ceil(206/20) = 11 páginas
    const resultsMatch = (doc.body && doc.body.innerText || '').match(/Results:\s*(\d+)/i);
    if (resultsMatch) {
      const total = parseInt(resultsMatch[1], 10);
      return Math.max(1, Math.ceil(total / 20));
    }
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
        const pagePosts = parsePage(doc);
        allPosts = allPosts.concat(pagePosts);
      } catch (e) {
        console.warn('Erro na página ' + p, e);
      }
    }
    const data = { thread_id: threadId, title: null, posts: allPosts };
    const jsonStr = JSON.stringify(data);
    try {
      await navigator.clipboard.writeText(jsonStr);
      alert('JSON copiado! (' + allPosts.length + ' posts de ' + maxPage + ' página(s)). Cole na caixa de texto do app e clique em "Carregar e analisar".');
    } catch (e) {
      prompt('Copie o JSON abaixo (Ctrl+C):', jsonStr);
    }
  })();
})();
