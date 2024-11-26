class UTVisualizer {
    constructor(timeline) {
        this.timeline = timeline;
        this.contentGroup = timeline.getContentGroup();
        this.mainGroup = timeline.getMainGroup();
        this.xScale = timeline.getScale();
        this.verticalPosition = 50;
        this.barHeight = 30;
    }

    visualize(ut) {
        // Clear previous content
        this.contentGroup.selectAll('*').remove();
        this.mainGroup.selectAll('.label-overlay').remove();

        const uniqueRatios = [...new Set(ut.events.map(d => d.metric_ratio))];
        
        const colorPalette = uniqueRatios.map((_, i) => {
            return d3.hsl(
                (i * 360 / uniqueRatios.length),
                0.5,
                0.7
            ).toString();
        });

        const colorScale = d3.scaleOrdinal()
            .domain(uniqueRatios)
            .range(colorPalette);

        const segments = this.contentGroup.selectAll('.segment')
            .data(ut.events)
            .enter()
            .append('rect')
            .attr('class', 'segment')
            .attr('x', d => this.xScale(d.start))
            .attr('y', this.verticalPosition)
            .attr('width', d => this.xScale(d.start + d.duration) - this.xScale(d.start))
            .attr('height', this.barHeight)
            .attr('fill', d => colorScale(d.metric_ratio))
            .attr('stroke', '#ccc') // light grey
            .attr('stroke-width', 1.75)
            .attr('vector-effect', 'non-scaling-stroke')
            .attr('data-original-color', d => colorScale(d.metric_ratio))
            .on('click', (event, d) => {
                const clickedSegment = d3.select(event.currentTarget);
                const wasSelected = clickedSegment.classed('selected');
                
                this.contentGroup.selectAll('.segment')
                    .classed('selected', false)
                    .attr('fill', function() {
                        return d3.select(this).attr('data-original-color');
                    })
                    .attr('stroke', '#ccc');

                if (!wasSelected) {
                    clickedSegment.classed('selected', true);
                    const originalColor = d3.hsl(clickedSegment.attr('data-original-color'));
                    originalColor.s *= 1.5;
                    originalColor.l *= 0.75;
                    clickedSegment
                        .attr('fill', originalColor.toString())
                        .attr('stroke', '#fff')
                        .attr('stroke-width', 2.5);
                }
                
                event.stopPropagation();
            });

        // click handler to the main SVG to deselect
        this.timeline.getSVG().on('click', () => {
            this.contentGroup.selectAll('.segment')
                .classed('selected', false)
                .attr('fill', function() {
                    return d3.select(this).attr('data-original-color');
                })
                .attr('stroke', '#ccc');
        });

        // Create label overlay
        const labelOverlay = this.mainGroup.append('g')
            .attr('class', 'label-overlay')
            .attr('pointer-events', 'none');

        const labels = labelOverlay.selectAll('.label')
            .data(ut.events)
            .enter()
            .append('text')
            .attr('class', 'segment-label')
            .attr('y', this.verticalPosition + this.barHeight/2)
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'middle')
            .attr('fill', 'black')
            .attr('font-size', '12px')
            .text(d => d.metric_ratio);

        const updateLabels = () => {
            const transform = this.timeline.getCurrentTransform();
            // Get the transformed scale
            const newScale = transform.rescaleX(this.xScale);
            
            labels.each(function(d) {
                const label = d3.select(this);
                const segmentCenter = d.start + (d.duration / 2);
                // Use the transformed scale for positioning
                label.attr('x', newScale(segmentCenter));

                // Check if label should be visible
                const segmentWidth = newScale(d.start + d.duration) - newScale(d.start);
                const textWidth = this.getComputedTextLength();
                label.style('opacity', textWidth + 4 < segmentWidth ? 1 : 0);
            });
        };

        // Initial update
        updateLabels();

        // Update on zoom
        this.timeline.onZoom(() => {
            updateLabels();
        });
    }
}