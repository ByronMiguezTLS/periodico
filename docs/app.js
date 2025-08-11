const categories = ["Portada","Modelos","Herramientas","Regulación","Investigación","Seguridad","Hardware","Mercado"];

const $ = (q,el=document)=>el.querySelector(q);
const $$= (q,el=document)=>Array.from(el.querySelectorAll(q));

const state = { edition:null, filter:null, query:"", theme: localStorage.getItem('theme')||'dark' };

function setTheme(t){
  state.theme=t;
  localStorage.setItem('theme',t);
  document.documentElement.classList.toggle('light', t==='light');
}

$('#toggleTheme').addEventListener('click', (e)=>{
  e.preventDefault();
  setTheme(state.theme==='light'?'dark':'light');
});
setTheme(state.theme);

$('#search').addEventListener('input', (e)=>{
  state.query = e.target.value.toLowerCase();
  render();
});

function badge(label){
  const b=document.createElement('button');
  b.className='badge'+(state.filter===label?' active':'');
  b.textContent=label;
  b.onclick=()=>{ state.filter = (state.filter===label?null:label); render(); };
  return b;
}

function matchesQuery(item){
  const q = state.query.trim();
  if(!q) return true;
  return (item.title.toLowerCase().includes(q) || item.source.toLowerCase().includes(q) || item.summary.toLowerCase().includes(q));
}

function sectionEl(name, items){
  const sec = document.createElement('section');
  sec.className='sec';
  const h2 = document.createElement('h2');
  const btn = document.createElement('span'); btn.textContent='▼';
  h2.innerHTML = name; h2.appendChild(btn);
  const grid = document.createElement('div'); grid.className='grid';
  h2.onclick = ()=>{ grid.style.display = grid.style.display==='none' ? 'grid' : 'none'; btn.textContent = grid.style.display==='none'?'►':'▼'; };
  sec.appendChild(h2);
  items.filter(matchesQuery).forEach(it=> grid.appendChild(cardEl(it)));
  sec.appendChild(grid);
  return sec;
}

function cardEl(it){
  const a = document.createElement('article'); a.className='card';
  const h = document.createElement('h3');
  const link = document.createElement('a'); link.href = it.link; link.target='_blank'; link.rel='noopener'; link.textContent = it.title;
  h.appendChild(link);
  const meta = document.createElement('div'); meta.className='meta'; meta.textContent = `${it.source} • ${it.published.slice(0,10)}`;
  const p = document.createElement('p'); p.textContent = it.summary;
  a.appendChild(h); a.appendChild(meta); a.appendChild(p);
  return a;
}

async function load(){
  const res = await fetch('./data/edition.json', {cache:'no-store'});
  state.edition = await res.json();
  render();
}

function render(){
  if(!state.edition) return;
  const filters = $('#filters'); filters.innerHTML='';
  categories.forEach(c=> filters.appendChild(badge(c)));

  const hero = $('#hero'); hero.className='hero';
  hero.innerHTML='';
  state.edition.top.filter(matchesQuery).forEach(it=>{
    const c = document.createElement('div'); c.className='card';
    const h = document.createElement('h3');
    const link = document.createElement('a'); link.href=it.link; link.target='_blank'; link.rel='noopener'; link.textContent=it.title;
    h.appendChild(link);
    const meta = document.createElement('div'); meta.className='meta'; meta.textContent = `${it.source} • ${it.published.slice(0,10)}`;
    const p = document.createElement('p'); p.textContent = it.summary;
    c.appendChild(h); c.appendChild(meta); c.appendChild(p);
    hero.appendChild(c);
  });

  const content = $('#content'); content.innerHTML='';
  categories.filter(c=>c!=="Portada").forEach(cat=>{
    if(state.filter && state.filter!==cat) return;
    const items = state.edition.sections[cat] || [];
    if(items.length) content.appendChild(sectionEl(cat, items));
  });
}

load();
