#!python
import pika
import json
import uuid

# 1. เชื่อมต่อกับ RabbitMQ Server
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', port=5672)
)
channel = connection.channel()

# 2. สร้าง Queue ชื่อ 'order_queue' (ถ้ามีอยู่แล้วมันจะไม่สร้างซ้ำ)
# durable=True คือถ้า RabbitMQ ดับ คิวจะไม่หาย
channel.queue_declare(queue='order_queue', durable=True)

def submit_order(product_name, quantity, price):
    # จำลองข้อมูล Order เป็น Dictionary
    order_data = {
        'order_id': str(uuid.uuid4()),
        'product': product_name,
        'quantity': quantity,
        'total_price': price * quantity,
        'status': 'pending'
    }

    # แปลงข้อมูลเป็น JSON String
    message = json.dumps(order_data)

    # 3. ส่งข้อมูลเข้า Exchange (Default Exchange ใช้ค่าว่าง '')
    channel.basic_publish(
        exchange='',
        routing_key='order_queue',
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,  # ทำให้ข้อความคงอยู่ (Persistent) แม้ RabbitMQ restart
        )
    )
    print(f" [x] Sent Order: {order_data['order_id']}")

# --- ทดลองส่ง Order ---
if __name__ == '__main__':
    submit_order("iPhone 15", 1, 32000)
    submit_order("AirPods Pro", 2, 8900)
    submit_order("MacBook Air", 1, 45000)

    # ปิดการเชื่อมต่อ
    connection.close()