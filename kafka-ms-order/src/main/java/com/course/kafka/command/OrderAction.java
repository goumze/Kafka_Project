package com.course.kafka.command;

import com.course.kafka.api.request.OrderItemRequest;
import com.course.kafka.api.request.OrderRequest;
import com.course.kafka.broker.message.OrderMessage;
import com.course.kafka.broker.producer.OrderProducer;
import com.course.kafka.entity.Order;
import com.course.kafka.entity.OrderItem;
import com.course.kafka.repository.OrderItemRepository;
import com.course.kafka.repository.OrderRepository;
import org.apache.commons.lang3.RandomStringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.stream.Collectors;

@Component
public class OrderAction {

    @Autowired
    private OrderProducer orderProducer;

    @Autowired
    private OrderRepository orderRepository;

    @Autowired
    private OrderItemRepository orderItemRepository;

    public Order convertToOrder(OrderRequest orderRequest) {
        var result = new Order();
        result.setCreditCardNumber(orderRequest.getCreditCardNumber());
        result.setOrderLocation(orderRequest.getOrderLocation());
        result.setOrderDateTime(LocalDateTime.now());
        result.setOrderNumber(RandomStringUtils.randomAlphanumeric(8).toUpperCase());

        var items = orderRequest.getItems()
                .stream()
                .map(this::convertToOrderItem)
                .collect(Collectors.toList());

        items.forEach(item -> item.setOrder(result));
        result.setItems(items);

        return result;
    }

    private OrderItem convertToOrderItem(OrderItemRequest orderItemRequest) {
        var result = new OrderItem();
        result.setItemName(orderItemRequest.getItemName());
        result.setPrice(orderItemRequest.getPrice());
        result.setQuantity(orderItemRequest.getQuantity());
        return result;
    }

    public void saveToDatabase(Order order){
        orderRepository.save(order);
        order.getItems().forEach(orderItemRepository::save);
    }

    public void publishToKafka(OrderItem orderItem){
        var orderMessage = new OrderMessage();
        orderMessage.setItemName(orderItem.getItemName());
        orderMessage.setPrice(orderItem.getPrice());
        orderMessage.setQuantity(orderItem.getQuantity());

        var order = orderItem.getOrder();
        orderMessage.setOrderDateTime(order.getOrderDateTime());
        orderMessage.setOrderLocation(order.getOrderLocation());
        orderMessage.setOrderNumber(order.getOrderNumber());
        orderMessage.setCreditCardNumber(order.getCreditCardNumber());
        orderProducer.publish(orderMessage);

    }


}
