// Future JavaScript for ChronoTech
console.log("ChronoTech is running!");

document.addEventListener('DOMContentLoaded', () => {
    const startRecognitionBtn = document.getElementById('start-recognition');
    const voiceStatus = document.getElementById('voice-status');
    const voiceResult = document.getElementById('voice-result');
    const descriptionField = document.getElementById('description');

    if (startRecognitionBtn) {
        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'fr-FR';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        startRecognitionBtn.addEventListener('click', () => {
            recognition.start();
            voiceStatus.textContent = 'Status: Listening...';
        });

        recognition.onresult = (event) => {
            const speechResult = event.results[0][0].transcript;
            voiceResult.textContent = 'Heard: ' + speechResult;
            
            // Attempt to automatically submit the form
            if(descriptionField) {
                descriptionField.value = speechResult;
                const form = descriptionField.closest('form');
                if (form) {
                    form.submit();
                }
            }

            voiceStatus.textContent = 'Status: Idle';
        };

        recognition.onspeechend = () => {
            recognition.stop();
            voiceStatus.textContent = 'Status: Idle';
        };

        recognition.onerror = (event) => {
            voiceStatus.textContent = 'Status: Error - ' + event.error;
        };
    }
});
