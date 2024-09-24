document.addEventListener('DOMContentLoaded', async () => {

    let currentIndex = 0;
    let images = [];
    let timestamps = [];
    let totalImages = 0;

    // DOM elements
    
    // Input text que almacena la fecha de interes
    const inputText = document.getElementById('input-text');

    // Boton que rellena inputText con la fecha actual
    const datetimeNowBtn = document.getElementById('datetime-now');

    // Boton que lanza el script de python para DOI
    const runScriptBtn = document.getElementById('run-script-btn');

    // <p> que muestra la FyH de captura de cada imagen
    const timestampDisplay = document.createElement('p');
    timestampDisplay.classList.add('timestamp-display');
    
    // Contenedro de las imagenes
    const imageContainer = document.getElementById('image-container');
    imageContainer.appendChild(timestampDisplay);
    
    // Botones previous and next. Control over images
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    
    // Contador de imagenes
    const imageCounter =  document.getElementById('image-counter');
    
    // Opaque overlay para cuando se esta ejecutando el script
    const overlay = document.getElementById('overlay');

    // Event listeners
    
    // Event listener for "Now!" button
    
    datetimeNowBtn.addEventListener('click', function() {
    
        // Get the current date, adjust to UTC-3, and format to 'YYYY-MM-DD HH:MM'
        const formattedDate = new Date(new Date().getTime() - 3 * 60 * 60 * 1000)
            .toISOString()
            .slice(0, 16)
            .replace('T', ' ');
        
            inputText.value = formattedDate;
    });

    
    // "Get Images!" button
    runScriptBtn.addEventListener('click', function() {

        // Disable navigation buttons while script is running
        prevBtn.disabled = true;
        nextBtn.disabled = true;
        // Opaque overlay while running
        overlay.style.display = 'block';

        // Get the input date that'll be passed to the python script
        const inputTextValue = inputText.value;
    
        // Send request to run Python script on the server
        fetch('/run-script', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({date_oi : inputTextValue})})

        .then(response => {
            
            if (response.ok) {
                
                // Once the script is successfully executed, load images
                loadImages();

            } else {

                console.error('Error running Python script');
            }
        })
        .catch(error => console.error('Error running script:', error));
    });


    
    prevBtn.addEventListener('click', () => {
        
        if (currentIndex > 0) {
        
            currentIndex--;

            updateImageDisplay();
        }
    });

    nextBtn.addEventListener('click', () => {

        if (currentIndex < totalImages - 1) {
        
            currentIndex++;
            
            updateImageDisplay();
        }
    });

    // Function to update image display
    function updateImageDisplay() {
    
        // Hide all images
        imageContainer.querySelectorAll('img').forEach(img => img.remove());

        if (images.length > 0) {

            const imgElement = document.createElement('img');

            imgElement.src = `/images/${images[currentIndex]}`;
            
            imgElement.classList.add('active');
            
            imageContainer.appendChild(imgElement);

            // Display timestamp
            timestampDisplay.textContent = `${timestamps[currentIndex]}`;
        }

        // Update button states
        prevBtn.disabled = (currentIndex === 0);
        nextBtn.disabled = (currentIndex === totalImages - 1);

        // Update image counter
        imageCounter.textContent = `${(currentIndex+1).toString().padStart(2,'0')}/${totalImages.toString().padStart(2,'0')}`;
    }

    // Fetch images and timestamps from server and display them
    function loadImages() {

        // Use Promise.all to fetch both images and timestamps at the same time
        Promise.all([
            fetch('/images').then(response => response.json()),
            fetch('/timestamps').then(response => response.json())
        ])
        .then(([imagesData, timestampsData]) => {
            // Set images and timestamps data
            images = imagesData;
            timestamps = timestampsData;

            // Update total images count and current index
            totalImages = images.length;
            currentIndex = 0;

            // Update the image display
            updateImageDisplay();

            // Enable navigation buttons after images are loaded
            prevBtn.disabled = (totalImages === 0);
            nextBtn.disabled = (totalImages === 0);

            // Disable Opaque overlay while running
            overlay.style.display = 'none';

        })
        .catch(error => console.error('Error loading images or timestamps:', error));
    }


    // Load images on initial page load
    loadImages();
});
