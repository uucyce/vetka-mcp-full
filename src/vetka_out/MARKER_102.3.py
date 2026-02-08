// MARKER_102.3_START
// Интеграция барабана файлов в секцию закрепленных файлов командного чата

class FileDrumIntegration {
  constructor() {
    this.pinnedFilesSection = document.querySelector('.pinned-files-section');
    this.fileDrum = document.querySelector('.file-drum-container');
    this.cameraOverlay = document.querySelector('.camera-overlay');
    this.artifactModal = document.querySelector('.artifact-modal');
  }

  init() {
    if (this.pinnedFilesSection && this.fileDrum) {
      this.integrateFileDrum();
      this.setupCameraLogic();
      this.setupArtifactOpening();
    }
  }

  integrateFileDrum() {
    // Вставка барабана файлов в секцию закрепленных файлов
    this.pinnedFilesSection.appendChild(this.fileDrum);
    this.fileDrum.classList.add('integrated-in-pinned');
  }

  setupCameraLogic() {
    const fileItems = this.fileDrum.querySelectorAll('.file-item');
    
    fileItems.forEach(item => {
      item.addEventListener('click', (e) => {
        const fileId = e.currentTarget.dataset.fileId;
        this.showCameraOverlay(fileId);
      });
    });
  }

  showCameraOverlay(fileId) {
    // Логика наезда камеры на файл
    this.cameraOverlay.classList.add('active');
    this.cameraOverlay.dataset.targetFile = fileId;
    
    // Закрытие по клику вне области
    this.cameraOverlay.addEventListener('click', (e) => {
      if (e.target === this.cameraOverlay) {
        this.hideCameraOverlay();
      }
    });
  }

  hideCameraOverlay() {
    this.cameraOverlay.classList.remove('active');
    delete this.cameraOverlay.dataset.targetFile;
  }

  setupArtifactOpening() {
    const artifactTriggers = this.fileDrum.querySelectorAll('.artifact-trigger');
    
    artifactTriggers.forEach(trigger => {
      trigger.addEventListener('click', (e) => {
        e.stopPropagation();
        const artifactId = e.currentTarget.dataset.artifactId;
        this.openArtifact(artifactId);
      });
    });
  }

  openArtifact(artifactId) {
    // Открытие артефакта с сохранением логики
    this.artifactModal.classList.add('open');
    this.artifactModal.dataset.artifactId = artifactId;
    
    // Загрузка содержимого артефакта
    this.loadArtifactContent(artifactId);
    
    // Закрытие модального окна
    const closeBtn = this.artifactModal.querySelector('.close-btn');
    closeBtn.addEventListener('click', () => {
      this.closeArtifact();
    });
  }

  loadArtifactContent(artifactId) {
    // Логика загрузки содержимого артефакта
    const artifactContent = this.artifactModal.querySelector('.artifact-content');
    artifactContent.innerHTML = `<div class="loading">Загрузка артефакта...</div>`;
    
    // Имитация загрузки
    setTimeout(() => {
      artifactContent.innerHTML = `<div class="artifact-data">Содержимое артефакта #${artifactId}</div>`;
    }, 500);
  }

  closeArtifact() {
    this.artifactModal.classList.remove('open');
    delete this.artifactModal.dataset.artifactId;
  }
}

// Инициализация интеграции
document.addEventListener('DOMContentLoaded', () => {
  const integration = new FileDrumIntegration();
  integration.init();
});

// MARKER_102.3_END