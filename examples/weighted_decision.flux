// A weighted decision: an intention holds a belief about which action
// is appropriate, then collapses it into a single commitment.
//
// Try running with different --seed values to see the distribution
// emerge across runs.

intention Decide {
    trigger: on_boot()
    priority: 0.8
    execute: {
        let actions = dist {
            "wait":    0.5,
            "explore": 0.3,
            "act":     0.2
        };

        let chosen = collapse(actions, weighted_random);
        send("mental_image", "chose: " ++ chosen, 1s);

        // The most-likely action, regardless of the sample.
        let mode = collapse(actions, max_weight);
        send("inner_voice", "mode is: " ++ mode, 500ms);
    }
}
