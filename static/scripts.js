// Timer functionality
function startExam(duration) {
    let timer = duration * 60;
    const display = document.getElementById('time-remaining');
    
    const interval = setInterval(() => {
        const minutes = Math.floor(timer / 60);
        let seconds = timer % 60;
        
        seconds = seconds < 10 ? "0" + seconds : seconds;
        display.textContent = minutes + ":" + seconds;
        
        if (--timer < 0) {
            clearInterval(interval);
            alert("Time's up! Submitting exam...");
            document.getElementById('exam-form').submit();
        }
        
        // Warning colors
        if (timer < 300) { // 5 minutes left
            display.parentElement.style.backgroundColor = '#e74c3c';
        } else if (timer < 600) { // 10 minutes left
            display.parentElement.style.backgroundColor = '#f39c12';
        }
    }, 1000);
}

// Calculator modal
function openCalculator() {
    const modal = document.createElement('div');
    modal.className = 'calculator-modal';
    modal.innerHTML = `
        <div class="calculator">
            <div class="calculator-display">0</div>
            <div class="calculator-keys">
                <!-- Calculator buttons -->
            </div>
            <button class="close-calculator">Close</button>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.querySelector('.close-calculator').addEventListener('click', () => {
        document.body.removeChild(modal);
    });
}

// Save answers automatically
setInterval(() => {
    const answers = {};
    document.querySelectorAll('.question').forEach(q => {
        const selected = q.querySelector('input[type="radio"]:checked');
        if (selected) {
            answers[selected.name] = selected.value;
        }
    });
    document.getElementById('answers').value = JSON.stringify(answers);
}, 5000);