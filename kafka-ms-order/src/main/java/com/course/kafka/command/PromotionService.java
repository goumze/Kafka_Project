package com.course.kafka.command;

import com.course.kafka.api.request.PromotionRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class PromotionService {

    @Autowired
    private PromotionAction action;

    public void createPromotion(PromotionRequest promotionRequest){
        action.publishToKafka(promotionRequest);
    }
}
