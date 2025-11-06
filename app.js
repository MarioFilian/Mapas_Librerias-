const map = L.map('map').setView([-1.8312, -78.1834], 7); // Ecuador

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
}).addTo(map);

fetch('markers.json')
  .then(response => response.json())
  .then(data => {
    data.forEach(location => {
      const marker = L.marker([location.lat, location.lon]).addTo(map);

      marker.on('click', () => {
        document.getElementById('info').innerHTML = `
          <h2>${location.parroquia}</h2>
          <p><strong>Provincia:</strong> ${location.provincia}</p>
          <p><strong>Cantón:</strong> ${location.canton}</p>
          <p><strong>Librerías:</strong></p>
          <ul>${location.librerias.map(l => `<li>${l}</li>`).join('')}</ul>
        `;
      });
    });
  })
  .catch(err => console.error('Error cargando los datos:', err));
