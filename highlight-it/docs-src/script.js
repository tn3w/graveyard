const THEME_KEY = 'highlightit-theme';
const THEMES = ['auto', 'light', 'dark'];

let themeIndex = 0;
let streamInterval = null;
let streamLine = 0;
let isPaused = false;

const rustCode = `use std::collections::HashMap;

fn main() {
    let mut scores = HashMap::new();
    
    scores.insert(String::from("Blue"), 10);
    scores.insert(String::from("Yellow"), 50);
    
    let team_name = String::from("Blue");
    let score = scores.get(&team_name);
    
    for (key, value) in &scores {
        println!("{}: {}", key, value);
    }
}`;

const codeLines = rustCode.split('\n');

function initTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored && THEMES.includes(stored)) {
        themeIndex = THEMES.indexOf(stored);
    }
    applyTheme();
}

function applyTheme() {
    const theme = THEMES[themeIndex];
    const html = document.documentElement;

    THEMES.forEach((t) => html.classList.remove(`highlightit-theme-${t}`));
    html.classList.add(`highlightit-theme-${theme}`);

    localStorage.setItem(THEME_KEY, theme);

    const label = document.getElementById('themeLabel');
    if (label) {
        label.textContent = `${theme.charAt(0).toUpperCase() + theme.slice(1)} Theme`;
    }
}

function toggleTheme() {
    themeIndex = (themeIndex + 1) % THEMES.length;
    applyTheme();
}

function startStream() {
    if (streamLine >= codeLines.length) {
        resetStream();
    }

    const startBtn = document.getElementById('streamStart');
    const pauseBtn = document.getElementById('streamPause');

    startBtn.disabled = true;
    pauseBtn.disabled = false;
    isPaused = false;

    streamInterval = setInterval(() => {
        if (streamLine < codeLines.length) {
            const code = document.getElementById('streamCode');
            const content = codeLines.slice(0, streamLine + 1).join('\n');
            code.textContent = content;

            streamLine++;
            updateProgress();
        } else {
            stopStream();
        }
    }, 150);
}

function pauseStream() {
    clearInterval(streamInterval);
    isPaused = true;

    const startBtn = document.getElementById('streamStart');
    const pauseBtn = document.getElementById('streamPause');

    startBtn.disabled = false;
    pauseBtn.disabled = true;
}

function stopStream() {
    clearInterval(streamInterval);

    const startBtn = document.getElementById('streamStart');
    const pauseBtn = document.getElementById('streamPause');

    startBtn.disabled = true;
    pauseBtn.disabled = true;
}

function resetStream() {
    clearInterval(streamInterval);
    streamLine = 0;

    const code = document.getElementById('streamCode');
    code.textContent = '// Code will stream here';

    const startBtn = document.getElementById('streamStart');
    const pauseBtn = document.getElementById('streamPause');

    startBtn.disabled = false;
    pauseBtn.disabled = true;

    updateProgress();
}

function updateProgress() {
    const bar = document.getElementById('streamBar');
    const percent = (streamLine / codeLines.length) * 100;
    bar.style.width = `${percent}%`;
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();

    HighlightIt.init({
        debounceTime: 40,
    });

    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    const streamStart = document.getElementById('streamStart');
    const streamPause = document.getElementById('streamPause');
    const streamReset = document.getElementById('streamReset');

    if (streamStart) streamStart.addEventListener('click', startStream);
    if (streamPause) streamPause.addEventListener('click', pauseStream);
    if (streamReset) streamReset.addEventListener('click', resetStream);

    const addDynamic = document.getElementById('addDynamic');
    const clearDynamic = document.getElementById('clearDynamic');
    const dynamicContainer = document.getElementById('dynamicContainer');

    const snippets = [
        {
            lang: 'javascript',
            code: `const greet = (name) => {
  return \`Hello, \${name}!\`;
};

console.log(greet('World'));`,
        },
        {
            lang: 'python',
            code: `def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(5))`,
        },
        {
            lang: 'rust',
            code: `fn main() {
    let numbers = vec![1, 2, 3, 4, 5];
    let sum: i32 = numbers.iter().sum();
    println!("Sum: {}", sum);
}`,
        },
    ];

    let counter = 0;

    if (addDynamic) {
        addDynamic.addEventListener('click', () => {
            const snippet = snippets[counter % snippets.length];
            counter++;

            const wrapper = document.createElement('div');
            wrapper.className = 'demo-card';
            wrapper.style.marginTop = '1rem';

            const pre = document.createElement('pre');
            pre.textContent = snippet.code;

            wrapper.appendChild(pre);
            dynamicContainer.appendChild(wrapper);

            HighlightIt.highlight(pre, {
                language: snippet.lang,
                withLines: true,
                addCopyButton: true,
            });
        });
    }

    if (clearDynamic) {
        clearDynamic.addEventListener('click', () => {
            dynamicContainer.innerHTML = '';
            counter = 0;
        });
    }
});
