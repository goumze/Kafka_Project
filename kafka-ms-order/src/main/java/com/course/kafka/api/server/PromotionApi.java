package com.course.kafka.api.server;

import com.course.kafka.api.request.PromotionRequest;
import com.course.kafka.command.PromotionService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/promotion")
public class PromotionApi {

    @Autowired
    private PromotionService promotionService;

    @PostMapping(value = "",consumes = MediaType.APPLICATION_JSON_VALUE, produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<String> create(@RequestBody PromotionRequest promotionRequest){
        promotionService.createPromotion(promotionRequest);
        return ResponseEntity.status(HttpStatus.CREATED).body(promotionRequest.getPromotionCode());
    }
}
