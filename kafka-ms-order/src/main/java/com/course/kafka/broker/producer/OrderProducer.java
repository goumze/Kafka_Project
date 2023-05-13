package com.course.kafka.broker.producer;

import com.course.kafka.broker.message.OrderMessage;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.concurrent.ListenableFutureCallback;

@Service
public class OrderProducer {

    @Autowired
    private KafkaTemplate<String, OrderMessage> kafkaTemplate;

    public void publish(OrderMessage orderMessage){
        kafkaTemplate.send("t-commodity-order",orderMessage.getOrderNumber(),orderMessage);
    }
}
