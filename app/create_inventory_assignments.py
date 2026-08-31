from . import create_app
from .models import db

app = create_app()

with app.app_context():
    inspector = db.inspect(db.engine)

    if "inventory_assignments" not in inspector.get_table_names():
        db.session.execute(
            db.text(
                """
                CREATE TABLE inventory_assignments (
                    id SERIAL PRIMARY KEY,

                    item_id INTEGER NOT NULL
                        REFERENCES inventory_items(id)
                        ON DELETE CASCADE,

                    assigned_user_id INTEGER
                        REFERENCES users(id),

                    assigned_to VARCHAR(128) NOT NULL,

                    assigned_department VARCHAR(128),

                    assigned_factory_id INTEGER
                        REFERENCES factories(id),

                    assigned_at TIMESTAMP NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    returned_at TIMESTAMP,

                    returned_to_user_id INTEGER
                        REFERENCES users(id),

                    delivered_by VARCHAR(128),

                    note TEXT,

                    created_at TIMESTAMP NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )

        db.session.execute(
            db.text(
                """
                CREATE INDEX ix_inventory_assignments_item_id
                ON inventory_assignments(item_id);
                """
            )
        )

        db.session.execute(
            db.text(
                """
                CREATE INDEX ix_inventory_assignments_assigned_user_id
                ON inventory_assignments(assigned_user_id);
                """
            )
        )

        db.session.execute(
            db.text(
                """
                CREATE INDEX ix_inventory_assignments_assigned_at
                ON inventory_assignments(assigned_at);
                """
            )
        )

        db.session.commit()

        print("OK: inventory_assignments tablosu oluşturuldu.")
    else:
        print("OK: inventory_assignments tablosu zaten mevcut.")
