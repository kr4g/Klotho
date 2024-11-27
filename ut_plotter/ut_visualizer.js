class UTVisualizer {
    constructor(timeline) {
        this.timeline = timeline;
        this.contentGroup = timeline.getContentGroup();
        this.mainGroup = timeline.getMainGroup();
        this.xScale = timeline.getScale();
        this.verticalPosition = 30;
        this.barHeight = 30;
    }

    visualize(ut) {
        // Clear previous content
        this.contentGroup.selectAll('*').remove();
        this.mainGroup.selectAll('.label-overlay').remove();

        // Calculate the full UT time range
        const utStart = Math.min(...ut.events.map(d => d.start));
        const utEnd = Math.max(...ut.events.map(d => d.start + d.duration));

        // Create label overlay in the main group for proper scaling
        const labelOverlay = this.mainGroup.append('g')
            .attr('class', 'label-overlay')
            .attr('pointer-events', 'none');

        // Add the selection tab (horizontal bar)
        const tab = this.contentGroup.append('rect')
            .attr('class', 'ut-tab')
            .attr('x', this.xScale(utStart))
            .attr('y', this.verticalPosition - 12)
            .attr('width', this.xScale(utEnd) - this.xScale(utStart))
            .attr('height', 40)
            .attr('fill', 'rgba(136, 136, 136, 0.6)')
            .attr('rx', 2)
            .attr('ry', 2)
            .style('cursor', 'pointer');

        // Add the UT label
        const utNumber = ut.id || '1';
        const utLabel = labelOverlay.append('text')
            .attr('class', 'ut-label')
            .attr('y', this.verticalPosition - 4)
            .attr('fill', 'white')
            .style('font-size', '12px')
            .style('font-family', 'Arial, sans-serif');

        // Add "UT" text and subscript number
        utLabel.append('tspan')
            .text('UT')
            .style('font-size', '8px');
        utLabel.append('tspan')
            .text(utNumber)
            .style('font-size', '6px')
            .attr('dy', '2')
            .attr('dx', '1');

        // Function to update label position during zoom
        const updateLabel = () => {
            const transform = this.timeline.getCurrentTransform();
            const newScale = transform.rescaleX(this.xScale);
            
            const visibleStart = newScale.invert(-transform.x / transform.k);
            const utEndPos = newScale(utEnd);
            
            if (utEndPos < 0) {
                utLabel.attr('x', newScale(utStart) + 5);
            } else if (utStart < visibleStart) {
                utLabel.attr('x', 5);
            } else {
                utLabel.attr('x', newScale(utStart) + 5);
            }
        };

        // Initial label position
        updateLabel();

        // Add click handler for the tab
        tab.on('click', (event) => {
            const allSegments = this.contentGroup.selectAll('.segment');
            const anySelected = allSegments.filter('.selected').size() > 0;
            
            if (anySelected) {
                // Deselect all
                allSegments
                    .classed('selected', false)
                    .attr('fill', function() {
                        return d3.select(this).attr('data-original-color');
                    })
                    .attr('stroke', '#ccc');
                
                tab.attr('fill', 'rgba(136, 136, 136, 0.6)');
                this.contentGroup.select('.ut-border').remove();
                this.timeline.clearTimeGuides();
            } else {
                // Select all segments
                allSegments.each(function() {
                    const segment = d3.select(this);
                    const originalColor = d3.hsl(segment.attr('data-original-color'));
                    originalColor.s *= 1.5;
                    originalColor.l *= 0.75;
                    segment
                        .classed('selected', true)
                        .attr('fill', originalColor.toString())
                        .attr('stroke', 'none');
                });
                
                tab.attr('fill', 'rgba(170, 170, 170, 0.8)');
                
                // Add border around the entire UT
                this.contentGroup.append('rect')
                    .attr('class', 'ut-border')
                    .attr('x', this.xScale(utStart))
                    .attr('y', this.verticalPosition)
                    .attr('width', this.xScale(utEnd) - this.xScale(utStart))
                    .attr('height', this.barHeight)
                    .attr('fill', 'none')
                    .attr('stroke', '#fff')
                    .attr('stroke-width', 2.5)
                    .attr('pointer-events', 'none');
                
                this.timeline.showTimeGuides(utStart, utEnd);
            }
            
            event.stopPropagation();
        });

        // Add click handler to SVG for deselection
        this.timeline.getSVG().on('click', () => {
            this.contentGroup.selectAll('.segment')
                .classed('selected', false)
                .attr('fill', function() {
                    return d3.select(this).attr('data-original-color');
                })
                .attr('stroke', '#ccc');
            
            tab.attr('fill', 'rgba(136, 136, 136, 0.6)');
            this.contentGroup.select('.ut-border').remove();
            this.timeline.clearTimeGuides();
        });

        // Create the segments (existing code)
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
                
                // Clear all selections
                this.contentGroup.selectAll('.segment')
                    .classed('selected', false)
                    .attr('fill', function() {
                        return d3.select(this).attr('data-original-color');
                    })
                    .attr('stroke', '#ccc');
                
                this.contentGroup.select('.ut-border').remove();
                this.timeline.clearTimeGuides();

                if (!wasSelected) {
                    // Handle single segment selection
                    clickedSegment.classed('selected', true);
                    const originalColor = d3.hsl(clickedSegment.attr('data-original-color'));
                    originalColor.s *= 1.5;
                    originalColor.l *= 0.75;
                    clickedSegment
                        .attr('fill', originalColor.toString())
                        .attr('stroke', '#fff')
                        .attr('stroke-width', 2.5);
                    
                    this.timeline.showTimeGuides(d.start, d.start + d.duration);
                }
                
                event.stopPropagation();
            });

        // Use the existing labelOverlay from earlier in the file
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

        // Update zoom handlers
        this.timeline.onZoom(() => {
            updateLabel();
            updateLabels();  // This is the existing function for segment labels
        });
    }
}