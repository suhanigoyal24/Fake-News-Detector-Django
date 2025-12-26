class NewsRouter:
    """
    A router to control all database operations on models in the 'detector' app.
    Specifically, it routes news-related models to 'news_db' and everything else to 'default'.
    """

    route_app_labels = {'detector'}  # all models in 'detector' app go to news_db

    def db_for_read(self, model, **hints):
        """
        Attempts to read detector models go to news_db.
        """
        if model._meta.app_label in self.route_app_labels:
            return 'news_db'
        return 'default'

    def db_for_write(self, model, **hints):
        """
        Attempts to write detector models go to news_db.
        """
        if model._meta.app_label in self.route_app_labels:
            return 'news_db'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow any relation if both models are in the detector app.
        """
        if (
            obj1._meta.app_label in self.route_app_labels and
            obj2._meta.app_label in self.route_app_labels
        ):
            return True
        # Allow relations if neither is in detector app
        elif (
            obj1._meta.app_label not in self.route_app_labels and
            obj2._meta.app_label not in self.route_app_labels
        ):
            return True
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure detector app only appears in the news_db database.
        """
        if app_label in self.route_app_labels:
            return db == 'news_db'
        return db == 'default'
