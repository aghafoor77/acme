from extensions import db


class Upload(db.Model):
    id = db.Column(db.String(120), primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    vdata = db.Column(db.String(1000), nullable=False)
    status = db.Column(db.Boolean, default=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<Upload {self.id} - {self.email}>"
