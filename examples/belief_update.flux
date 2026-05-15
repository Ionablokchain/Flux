// Belief update: a mosaic stores observations under a single key,
// each with its own weight. Reading the mosaic gives the most probable
// value (`max_weight` is the default mosaic read policy). Sampling a
// distribution gives a different view of the same data.

causal_mosaic observations = sparse_temporal_matrix();

intention Observe {
    trigger: on_boot()
    priority: 0.9
    execute: {
        // Three observations of the same phenomenon, with different
        // confidences. The mosaic accumulates them under one key.
        observations.accept("weather").write("sunny", 0.2);
        observations.accept("weather").write("cloudy", 0.5);
        observations.accept("weather").write("rainy",  0.3);
        send("inner_voice", "observations recorded", 200ms);
    }
}

intention Believe {
    trigger: on_boot()
    priority: 0.5
    execute: {
        // The mosaic's default read returns the most probable value.
        let best_guess = observations.accept("weather").read();
        send("mental_image", "best guess: " ++ best_guess, 1s);

        // We can also lift the same observations into a distribution
        // literal and reason about them directly.
        let prior = dist {
            "sunny":  0.2,
            "cloudy": 0.5,
            "rainy":  0.3
        };
        let sample = collapse(prior, weighted_random);
        send("inner_voice", "sample: " ++ sample, 1s);
    }
}
