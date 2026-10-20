const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const script = fs.readFileSync(path.join(__dirname, '../app/static/theme.js'), 'utf8');
function page(saved, blocked = false) {
    const handlers = {};
    const elements = {
        'theme-toggle': { setAttribute(k, v) { this[k] = v; } },
        'theme-preference-note': {}
    };
    const storage = { value: saved };
    const context = {
        window: { addEventListener(k, fn) { handlers[k] = fn; } },
        document: {
            documentElement: { dataset: {} }, readyState: 'loading',
            getElementById: id => elements[id],
            addEventListener(k, fn) { handlers[k] = fn; }
        },
        localStorage: {
            getItem() { if (blocked) throw Error('blocked'); return storage.value; },
            setItem(k, v) { if (blocked) throw Error('blocked'); storage.value = v; }
        }
    };
    vm.createContext(context);
    vm.runInContext(script, context);
    return { context, elements, handlers, storage,
        click: () => handlers.click({ target: { closest: () => elements['theme-toggle'] } }) };
}
const p = page(null);
assert.equal(p.context.document.documentElement.dataset.theme, 'dark');
assert.equal(p.elements['theme-toggle']['aria-checked'], 'true');
p.click();
assert.equal(p.storage.value, 'light');
assert.equal(p.context.document.documentElement.dataset.theme, 'light');
assert.equal(p.elements['theme-toggle']['aria-checked'], 'false');
assert.equal(page(p.storage.value).context.document.documentElement.dataset.theme, 'light');
const originalClick = p.handlers.click;
vm.runInContext(script, p.context);
assert.equal(p.handlers.click, originalClick, 'duplicate head include must not register twice');
p.click();
assert.equal(p.storage.value, 'dark');
p.handlers.storage({ key: 'mioty-appearance', newValue: 'light' });
assert.equal(p.context.document.documentElement.dataset.theme, 'light');
p.handlers.storage({ key: null, newValue: null });
assert.equal(p.context.document.documentElement.dataset.theme, 'dark');
assert.equal(page('invalid').context.document.documentElement.dataset.theme, 'dark');
const denied = page(null, true);
denied.click();
assert.equal(denied.context.document.documentElement.dataset.theme, 'light');
assert.match(denied.elements['theme-preference-note'].textContent, /nur für diese Seite/);
console.log('Theme preference checks passed.');
