package com.course.kafka.command;

import com.course.kafka.api.request.OrderRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class OrderService {

    @Autowired
    private OrderAction orderAction;


    public String saveOrder(OrderRequest orderRequest) {
      var order = orderAction.convertToOrder(orderRequest);
      orderAction.saveToDatabase(order);

      //flatten message and publish
        order.getItems().forEach(orderAction::publishToKafka);
      return order.getOrderNumber();
    }


}
