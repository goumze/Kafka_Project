package com.course.kafka.broker.consumer;

import com.course.kafka.broker.message.OrderMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

@Service
public class OrderConsumer {
    private static final Logger LOG = LoggerFactory.getLogger(OrderConsumer.class);

    @KafkaListener(topics = "t-commodity-order")
    public void listen(OrderMessage message){
        var totalItemAmount = message.getPrice() * message.getQuantity();
        LOG.info("Processing Order {}, item {}, credit card number {}. Total amount for this item is {}",
                message.getOrderNumber(),message.getItemName(),message.getCreditCardNumber(),totalItemAmount);
    }
}
