// Fullscreen mode
document.addEventListener('DOMContentLoaded', function() {
    const fullscreenBtn = document.getElementById('fullscreen-btn');

    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', function() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(err => {
                    console.log('Fullscreen error:', err);
                });
                this.innerHTML = '<i class="ri-fullscreen-exit-line ri-lg"></i>';
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                    this.innerHTML = '<i class="ri-fullscreen-line ri-lg"></i>';
                }
            }
        });

        // Слушатель изменения fullscreen состояния
        document.addEventListener('fullscreenchange', function() {
            if (!document.fullscreenElement) {
                fullscreenBtn.innerHTML = '<i class="ri-fullscreen-line ri-lg"></i>';
            }
        });
    }
});