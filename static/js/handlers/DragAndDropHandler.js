 // Обработчик перетаскивания файлов
 function handleDrop(e) {
    e.preventDefault();
    const input = document.getElementById('file');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      input.files = e.dataTransfer.files;
    }
  }

  function handleDrag(e) {
    e.preventDefault();
  }

  export default { handleDrop, handleDrag };