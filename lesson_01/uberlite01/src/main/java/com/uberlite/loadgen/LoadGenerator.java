package com.uberlite.loadgen;

import com.uberlite.model.LocationEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Random;
import java.util.UUID;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

/**
 * Generates location events at a configurable rate.
 * Simulates multiple drivers generating GPS locations in San Francisco area.
 */
public class LoadGenerator {
    private static final Logger log = LoggerFactory.getLogger(LoadGenerator.class);
    private final Random random = new Random();
    private final int numDrivers;
    private final int eventsPerSecond;
    
    // San Francisco bounding box
    private static final double MIN_LAT = 37.7;
    private static final double MAX_LAT = 37.8;
    private static final double MIN_LON = -122.5;
    private static final double MAX_LON = -122.4;

    public LoadGenerator(int numDrivers, int eventsPerSecond) {
        this.numDrivers = numDrivers;
        this.eventsPerSecond = eventsPerSecond;
        log.info("LoadGenerator initialized: {} drivers, {} events/sec", numDrivers, eventsPerSecond);
    }

    public void start(Consumer<LocationEvent> eventConsumer) {
        var executor = Executors.newVirtualThreadPerTaskExecutor();
        
        var driverIds = new String[numDrivers];
        for (int i = 0; i < numDrivers; i++) {
            driverIds[i] = "driver-" + UUID.randomUUID().toString().substring(0, 8);
        }
        
        var intervalNs = 1_000_000_000L / eventsPerSecond;
        
        executor.submit(() -> {
            var nextTime = System.nanoTime();
            long eventCount = 0;
            
            while (!Thread.currentThread().isInterrupted()) {
                var driverId = driverIds[random.nextInt(numDrivers)];
                var lat = MIN_LAT + (MAX_LAT - MIN_LAT) * random.nextDouble();
                var lon = MIN_LON + (MAX_LON - MIN_LON) * random.nextDouble();
                
                var event = new LocationEvent(driverId, lat, lon, System.currentTimeMillis());
                eventConsumer.accept(event);
                
                if (++eventCount % 10000 == 0) {
                    log.debug("Generated {} events", eventCount);
                }
                
                nextTime += intervalNs;
                var sleepNs = nextTime - System.nanoTime();
                if (sleepNs > 0) {
                    try {
                        TimeUnit.NANOSECONDS.sleep(sleepNs);
                    } catch (InterruptedException e) {
                        log.info("LoadGenerator interrupted");
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        });
    }
}