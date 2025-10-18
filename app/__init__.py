from datetime import datetime, timedelta

from flask import Flask, render_template


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html", active_page="index")

    @app.route("/talep-takip")
    def talep_takip():
        now = datetime.now()

        def make_item(
            *,
            hardware_type: str,
            brand: str,
            model: str,
            quantity: int,
            opened_delta: timedelta,
            note: str,
        ) -> dict:
            opened_at = now - opened_delta
            return {
                "hardware_type": hardware_type,
                "brand": brand,
                "model": model,
                "quantity": quantity,
                "note": note,
                "opened_display": opened_at.strftime("%d.%m.%Y %H:%M"),
            }

        def make_order(
            *,
            order_no: str,
            requested_by: str,
            department: str,
            opened_delta: timedelta,
            lines: list[dict],
        ) -> dict:
            opened_at = now - opened_delta
            opened_display = opened_at.strftime("%d.%m.%Y %H:%M")
            search_tokens = [order_no, requested_by, department, opened_display]
            for item in lines:
                search_tokens.extend(
                    [
                        item.get("hardware_type"),
                        item.get("brand"),
                        item.get("model"),
                        item.get("note"),
                    ]
                )

            token_string = " ".join(token for token in search_tokens if token)

            return {
                "order_no": order_no,
                "requested_by": requested_by,
                "department": department,
                "opened_display": opened_display,
                "lines": lines,
                "item_count": len(lines),
                "total_quantity": sum(item["quantity"] for item in lines),
                "search_index": token_string.lower(),
            }

        request_groups = [
            {
                "key": "acik",
                "label": "Açık",
                "description": "Açıkta bekleyen talepler buradan yönetilir.",
                "empty_message": "Bu statüde görüntülenecek açık talep bulunmuyor.",
                "orders": [
                    make_order(
                        order_no="SIP-2024-015",
                        requested_by="Merve Çetin",
                        department="IT Operasyon",
                        opened_delta=timedelta(hours=2, minutes=45),
                        lines=[
                            make_item(
                                hardware_type="Laptop",
                                brand="Dell",
                                model="Latitude 5440",
                                quantity=2,
                                opened_delta=timedelta(hours=2, minutes=45),
                                note="Saha ekibi için yedek cihazlar",
                            ),
                            make_item(
                                hardware_type="Monitör",
                                brand="Dell",
                                model="P2422H",
                                quantity=2,
                                opened_delta=timedelta(hours=2, minutes=30),
                                note="Yeni laptoplarla birlikte gönderilecek",
                            ),
                        ],
                    ),
                    make_order(
                        order_no="SIP-2024-018",
                        requested_by="Ahmet Kaya",
                        department="Satın Alma",
                        opened_delta=timedelta(days=1, hours=3),
                        lines=[
                            make_item(
                                hardware_type="Yazıcı",
                                brand="HP",
                                model="LaserJet Pro M404",
                                quantity=1,
                                opened_delta=timedelta(days=1, hours=3),
                                note="Merkez ofis için yedek yazıcı",
                            )
                        ],
                    ),
                ],
            },
            {
                "key": "kapandi",
                "label": "Kapandı",
                "description": "Stoklara giren ve tamamlanan taleplerin özeti.",
                "empty_message": "Kapanmış talep kaydı bulunmuyor.",
                "orders": [
                    make_order(
                        order_no="SIP-2024-009",
                        requested_by="Zeynep Uçar",
                        department="Operasyon",
                        opened_delta=timedelta(days=3, hours=5),
                        lines=[
                            make_item(
                                hardware_type="Sunucu",
                                brand="Lenovo",
                                model="ThinkSystem SR250",
                                quantity=1,
                                opened_delta=timedelta(days=2, hours=12),
                                note="Veri merkezi genişletme talebi",
                            )
                        ],
                    ),
                    make_order(
                        order_no="SIP-2024-011",
                        requested_by="Berk Tan",
                        department="Depo",
                        opened_delta=timedelta(days=2, hours=8),
                        lines=[
                            make_item(
                                hardware_type="Tarayıcı",
                                brand="Fujitsu",
                                model="fi-7160",
                                quantity=3,
                                opened_delta=timedelta(days=2, hours=6),
                                note="Yeni şube teslim alındı",
                            )
                        ],
                    ),
                ],
            },
            {
                "key": "iptal",
                "label": "İptal",
                "description": "İptal edilen talepler ve nedenlerine buradan ulaşabilirsiniz.",
                "empty_message": "İptal edilmiş talep kaydı bulunmuyor.",
                "orders": [
                    make_order(
                        order_no="SIP-2024-006",
                        requested_by="Elif Sönmez",
                        department="Finans",
                        opened_delta=timedelta(days=5, hours=4),
                        lines=[
                            make_item(
                                hardware_type="Masaüstü",
                                brand="HP",
                                model="ProDesk 400",
                                quantity=1,
                                opened_delta=timedelta(days=4, hours=21),
                                note="Bütçe onayı alınamadı",
                            )
                        ],
                    ),
                    make_order(
                        order_no="SIP-2024-010",
                        requested_by="Pelin Arı",
                        department="Pazarlama",
                        opened_delta=timedelta(days=4, hours=10),
                        lines=[
                            make_item(
                                hardware_type="Tablet",
                                brand="Apple",
                                model="iPad Air",
                                quantity=4,
                                opened_delta=timedelta(days=4, hours=9),
                                note="Etkinlik ertelendiği için iptal edildi",
                            )
                        ],
                    ),
                ],
            },
        ]

        hardware_catalog = {
            "types": [
                "Laptop",
                "Masaüstü",
                "Monitör",
                "Sunucu",
                "Yazıcı",
                "Tarayıcı",
                "Tablet",
                "Aksesuar",
            ],
            "brands": [
                "Apple",
                "Asus",
                "Dell",
                "Fujitsu",
                "HP",
                "Lenovo",
                "Logitech",
                "Microsoft",
                "Samsung",
            ],
            "models": [
                "Latitude 5440",
                "ThinkPad X1 Carbon",
                "ProDesk 400",
                "ProBook 450 G10",
                "LaserJet Pro M404",
                "P2422H",
                "ThinkSystem SR250",
                "fi-7160",
                "iPad Air",
            ],
        }

        return render_template(
            "talep_takip.html",
            active_page="talep_takip",
            request_groups=request_groups,
            hardware_catalog=hardware_catalog,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
