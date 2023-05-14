package com.course.kafka.command;

import com.course.kafka.api.request.PromotionRequest;
import com.course.kafka.broker.message.PromotionMessage;
import com.course.kafka.broker.producer.PromotionProducer;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class PromotionAction {

    @Autowired
    private PromotionProducer producer;
    public void publishToKafka(PromotionRequest promotionRequest) {
        var message = new PromotionMessage(promotionRequest.getPromotionCode());
        producer.publish(message);
    }
}
