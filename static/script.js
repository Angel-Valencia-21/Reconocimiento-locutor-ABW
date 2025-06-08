// Mostrar espectrograma en canvas
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

// Grabación de audio
let mediaRecorder;
let audioChunks = [];

const grabarBtn = document.getElementById("grabarBtn");

grabarBtn.onclick = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const audioContext = new AudioContext();
  const source = audioContext.createMediaStreamSource(stream);
  const analyser = audioContext.createAnalyser();
  source.connect(analyser);
  analyser.fftSize = 256;

  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  function draw() {
    requestAnimationFrame(draw);
    analyser.getByteFrequencyData(dataArray);
    ctx.fillStyle = "navy";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const barWidth = (canvas.width / bufferLength) * 2.5;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const barHeight = dataArray[i];
      ctx.fillStyle = "lime";
      ctx.fillRect(x, canvas.height - barHeight / 2, barWidth, barHeight / 2);
      x += barWidth + 1;
    }
  }

  draw();

  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = e => {
    audioChunks.push(e.data);
  };

  mediaRecorder.onstop = () => {
    const audioBlob = new Blob(audioChunks);
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);
    audio.play();
  };

  audioChunks = [];
  mediaRecorder.start();

  grabarBtn.textContent = "Detener grabación";
  grabarBtn.onclick = () => {
    mediaRecorder.stop();
    grabarBtn.textContent = "Grabar audio";
    grabarBtn.onclick = async () => grabarBtn.onclick(); // reiniciar función
  };
};

// Soporte para arrastrar y soltar
const dropArea = document.getElementById("drop-area");
dropArea.addEventListener("dragover", e => {
  e.preventDefault();
  dropArea.style.backgroundColor = "#ccc";
});
dropArea.addEventListener("dragleave", () => {
  dropArea.style.backgroundColor = "#e0e0e0";
});
dropArea.addEventListener("drop", e => {
  e.preventDefault();
  dropArea.style.backgroundColor = "#e0e0e0";
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    alert(`Archivo recibido: ${files[0].name}`);
  }
});

// Subida de archivo
document.getElementById("archivoAudio").addEventListener("change", e => {
  const archivo = e.target.files[0];
  if (archivo && archivo.name.endsWith(".wav")) {
    alert(`Seleccionaste: ${archivo.name}`);
  } else {
    alert("Por favor selecciona un archivo .wav");
  }
});
