#!python
import pika
import json
import time

# 1. เชื่อมต่อกับ RabbitMQ (เหมือนเดิม)
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost', port=5672)
)
channel = connection.channel()

# ประกาศ Queue อีกครั้งเพื่อให้มั่นใจว่ามี Queue นี้อยู่จริง (เผื่อรัน consumer ก่อน producer)
channel.queue_declare(queue='order_queue', durable=True)

print(' [*] Waiting for orders. To exit press CTRL+C')

# ฟังก์ชัน Callback ที่จะทำงานเมื่อมีข้อความเข้ามา
def callback(ch, method, properties, body):
    print(f" [x] Received Data...")
    
    # แปลง JSON กลับเป็น Python Dict
    order = json.loads(body)
    
    # จำลองการทำงาน (Processing)
    print(f"     Processing Order ID: {order['order_id']}")
    print(f"     Item: {order['product']} (Qty: {order['quantity']})")
    time.sleep(1) # จำลองว่าใช้เวลาทำงาน 1 วินาที
    
    print(" [v] Order Processed Done!")

    # สำคัญ! ส่ง Acknowledge บอก RabbitMQ ว่าทำงานเสร็จแล้ว (ลบออกจากคิวได้)
    ch.basic_ack(delivery_tag=method.delivery_tag)

# 2. ตั้งค่าการรับข้อมูล
# prefetch_count=1 คือให้ส่งงานมาทีละ 1 งาน ถ้ายังทำไม่เสร็จไม่ต้องส่งมาเพิ่ม (Fair dispatch)
channel.basic_qos(prefetch_count=1) 

channel.basic_consume(queue='order_queue', on_message_callback=callback)

# เริ่มวนลูปรอรับข้อมูล
channel.start_consuming()