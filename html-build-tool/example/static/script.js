document.addEventListener('DOMContentLoaded', () => {
    console.log('HTML Build Tool Example loaded!');

    const button = document.getElementById('demo-button');
    const output = document.getElementById('output');

    if (button && output) {
        button.addEventListener('click', () => {
            const timestamp = new Date().toLocaleTimeString();
            output.textContent = `Button clicked at ${timestamp}`;
            output.style.color = '#2563eb';
        });
    }
});
