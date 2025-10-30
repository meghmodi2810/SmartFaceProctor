from django.apps import AppConfig
import logging

logger = logging.getLogger('exam_monitoring')

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """
        Initialize exam monitoring system when Django starts.
        This runs once when Django starts in both development and production.
        """
        try:
            # Import monitoring cleanup utilities
            from .monitoring_cleanup import cleanup_on_server_start
            
            # Run server startup cleanup
            cleaned = cleanup_on_server_start()
            logger.info(f"Server startup: Cleaned {cleaned} stale monitoring sessions")
            
        except Exception as e:
            logger.error(f"Error initializing exam monitoring: {e}")
