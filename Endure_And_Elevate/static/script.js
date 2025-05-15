document.addEventListener("DOMContentLoaded", () => {
    function formatSecondsToMinutes(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    function parseMinutesSeconds(value) {
        const [minutes, seconds] = value.split(":").map(Number);
        return minutes * 60 + seconds;
    }

    const paceInputs = document.querySelectorAll("input[data-km]");

    paceInputs.forEach(input => {
        input.addEventListener("change", (event) => {
            const changedKm = event.target.dataset.km;
            const newValue = event.target.value; 

            const newPaceInSeconds = parseMinutesSeconds(newValue);

            fetch("/update_paces", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ changed_km: changedKm, new_pace: newPaceInSeconds })
            })
            .then(response => response.json())
            .then(updatedData => {
                
                Object.entries(updatedData).forEach(([km, pace]) => {
                    const spinbox = document.querySelector(`input[data-km="${km}"]`);
                    if (spinbox) {
                        spinbox.value = formatSecondsToMinutes(pace);
                    }
                });
            })
            .catch(error => console.error("Error updating paces:", error));
        });
    });
});