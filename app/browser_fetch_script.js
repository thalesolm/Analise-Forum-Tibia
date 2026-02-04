// Cole este script no Console (F12 → Console) enquanto estiver na página do tópico do Tibia.
// Ele baixa todas as páginas do tópico e copia o JSON para a área de transferência.
(function() {
  const params = new URLSearchParams(window.location.search);
  const threadId = params.get('threadid');
  if (!threadId) {
    alert('Abra uma página de tópico do fórum (URL deve conter threadid=).');
    return;
  }
  const dateRe = /\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}/;
  const postIdRe = /Post\s*#(\d+)/i;
  function parsePage(doc) {
    const posts = [];
    const seen = new Set();
    const links = doc.querySelectorAll('a[href*="subtopic=characters"][href*="name="]');
    for (const a of links) {
      const author = (a.textContent || '').trim();
      if (!author || author.length > 50) continue;
      if (/^(community|tibia|forum|board jump|thread jump|post jump|page jump)$/i.test(author)) continue;
      let el = a.parentElement;
      for (let i = 0; i < 20 && el; i++) {
        const text = (el.innerText || '').replace(/\s+/g, ' ');
        const dateMatch = text.match(dateRe);
        if (dateMatch) {
          const dateStr = dateMatch[0];
          const key = author + '|' + dateStr;
          if (seen.has(key)) break;
          seen.add(key);
          let body = text.replace(dateStr, '').replace(/Edited by [^\n]+ on \d{2}\.\d{2}\.\d{4}[^\n]*/gi, '').replace(/_+/g, '').replace(/\s+/g, ' ').trim();
          const postIdMatch = text.match(postIdRe);
          posts.push({ post_id: postIdMatch ? postIdMatch[1] : null, author, date: dateStr, body });
          break;
        }
        el = el.parentElement;
      }
    }
    return posts;
  }
  const baseUrl = window.location.origin + window.location.pathname + '?' + new URLSearchParams({ action: 'thread', threadid: threadId }).toString();
  const pageLinks = Array.from(document.querySelectorAll('a[href*="pagenumber="]'));
  const pageNumbers = pageLinks.map(a => {
    const m = (a.getAttribute('href') || '').match(/pagenumber=(\d+)/);
    return m ? parseInt(m[1], 10) : null;
  }).filter(Boolean);
  const maxPage = pageNumbers.length ? Math.max(...pageNumbers) : 1;
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
      alert('JSON copiado! (' + allPosts.length + ' posts). Cole na caixa de texto do app e clique em "Carregar e analisar".');
    } catch (e) {
      prompt('Copie o JSON abaixo (Ctrl+C):', jsonStr);
    }
  })();
})();
