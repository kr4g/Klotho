class Timeline {
    constructor(container) {
        this.container = d3.select(container);
        
        // Set dimensions
        this.margin = { top: 50, right: 20, bottom: 20, left: 20 };
        this.width = this.container.node().getBoundingClientRect().width - this.margin.left - this.margin.right;
        this.height = 400 - this.margin.top - this.margin.bottom;

        // Initialize base timeline (0 to 60 seconds)
        this.xScale = d3.scaleLinear()
            .domain([0, 60])
            .range([0, this.width]);

        this.setupTimeline();
        this.setupZoom();
        this.setupGuides();
    }

    setupTimeline() {
        // Create SVG
        this.svg = this.container.append('svg')
            .attr('width', '100%')
            .attr('height', this.height + this.margin.top + this.margin.bottom);

        // Main group
        this.mainGroup = this.svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        // Clip path for content
        this.svg.append('defs').append('clipPath')
            .attr('id', 'timeline-clip')
            .append('rect')
            .attr('width', this.width)
            .attr('height', this.height);

        // Timeline axis
        this.axisGroup = this.mainGroup.append('g')
            .attr('class', 'timeline-axis');

        // Content group (for UTs)
        this.contentGroup = this.mainGroup.append('g')
            .attr('class', 'content')
            .attr('clip-path', 'url(#timeline-clip)');

        // Draw initial axis
        this.updateAxis();
    }

    setupZoom() {
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 50])
            .wheelDelta((event) => {
                return event.ctrlKey || event.shiftKey ? 
                    -event.deltaY * 0.01 : 
                    -event.deltaY * 0.002;
            })
            .on('zoom', (event) => {
                this.currentTransform = event.transform;
                
                // Update axis with transformed scale
                const newScale = this.currentTransform.rescaleX(this.xScale);
                this.updateAxis(newScale);
                
                // Update content group transformation
                this.contentGroup.attr('transform', 
                    `translate(${event.transform.x},0) scale(${event.transform.k},1)`
                );
                
                // Update guide positions if they exist
                if (this.guideStartTime !== undefined) {
                    const startGuide = this.guideGroup.select('.start-guide');
                    const endGuide = this.guideGroup.select('.end-guide');
                    
                    if (!startGuide.empty() && !endGuide.empty()) {
                        startGuide
                            .attr('x1', newScale(this.guideStartTime))
                            .attr('x2', newScale(this.guideStartTime));
                        
                        endGuide
                            .attr('x1', newScale(this.guideEndTime))
                            .attr('x2', newScale(this.guideEndTime));
                    }

                    // Update time markers
                    this.axisGroup.select('.start-time')
                        .attr('transform', `translate(${newScale(this.guideStartTime)},0)`)
                        .select('text')
                        .attr('fill', 'white');
                    this.axisGroup.select('.end-time')
                        .attr('transform', `translate(${newScale(this.guideEndTime)},0)`)
                        .select('text')
                        .attr('fill', 'white');

                    // Remove any ticks that are too close to our markers
                    this.axisGroup.selectAll('.tick')
                        .filter(d => {
                            const tickPos = newScale(d);
                            const startPos = newScale(this.guideStartTime);
                            const endPos = newScale(this.guideEndTime);
                            return Math.abs(tickPos - startPos) < 30 || Math.abs(tickPos - endPos) < 30;
                        })
                        .remove();
                }
                
                if (this.zoomCallback) {
                    this.zoomCallback(event.transform);
                }
            });

        this.svg.call(this.zoom);
    }

    updateAxis(scale = this.xScale) {
        const axis = d3.axisTop(scale)
            .tickFormat(d => d.toFixed(1))
            .tickSizeOuter(0)
            .tickSize(6)  // Main tick size
            .ticks(20);   // Increase number of ticks

        // Add the main axis
        this.axisGroup.call(axis);
        
        // Add minor ticks
        const minorAxis = d3.axisTop(scale)
            .tickSize(4)
            .ticks(100)
            .tickFormat('');  // No labels for minor ticks
            
        this.axisGroup.append('g')
            .attr('class', 'minor-ticks')
            .call(minorAxis);
    }

    getContentGroup() {
        return this.contentGroup;
    }

    getScale() {
        return this.xScale;
    }

    getCurrentTransform() {
        return this.currentTransform || d3.zoomIdentity;
    }

    onZoom(callback) {
        this.zoomCallback = callback;
    }

    getMainGroup() {
        return this.mainGroup;
    }

    getSVG() {
        return this.svg;
    }

    setupGuides() {
        // Create a group for the selection guides
        this.guideGroup = this.mainGroup.append('g')
            .attr('class', 'selection-guides')
            .attr('pointer-events', 'none');
    }

    showTimeGuides(startTime, endTime) {
        // Clear existing guides
        this.guideGroup.selectAll('*').remove();

        const transform = this.getCurrentTransform();
        const newScale = transform.rescaleX(this.xScale);

        // Add start guide
        this.guideGroup.append('line')
            .attr('class', 'time-guide start-guide')
            .attr('x1', newScale(startTime))
            .attr('y1', 0)
            .attr('x2', newScale(startTime))
            .attr('y2', 50)
            .attr('stroke', 'white')
            .attr('stroke-width', 1)
            .attr('stroke-dasharray', '4,4');

        // Add end guide
        this.guideGroup.append('line')
            .attr('class', 'time-guide end-guide')
            .attr('x1', newScale(endTime))
            .attr('y1', 0)
            .attr('x2', newScale(endTime))
            .attr('y2', 50)
            .attr('stroke', 'white')
            .attr('stroke-width', 1)
            .attr('stroke-dasharray', '4,4');

        // Store the times for updating during zoom
        this.guideStartTime = startTime;
        this.guideEndTime = endTime;

        // Remove any existing ticks that are too close to our markers
        this.axisGroup.selectAll('.tick')
            .filter(d => {
                const tickPos = newScale(d);
                const startPos = newScale(startTime);
                const endPos = newScale(endTime);
                return Math.abs(tickPos - startPos) < 30 || Math.abs(tickPos - endPos) < 30;
            })
            .remove();

        // Add custom time markers that will persist
        const addTimeMarker = (time, className) => {
            this.axisGroup.append('g')
                .attr('class', `time-marker ${className}`)
                .attr('transform', `translate(${newScale(time)},0)`)
                .call(g => {
                    g.append('line')
                        .attr('y2', 6)
                        .attr('stroke', 'white');
                    g.append('text')
                        .attr('class', 'time-marker-text')
                        .attr('y', -9)
                        .attr('text-anchor', 'middle')
                        .attr('fill', 'white')
                        .text(time.toFixed(3));
                });
        };

        addTimeMarker(startTime, 'start-time');
        addTimeMarker(endTime, 'end-time');
    }

    clearTimeGuides() {
        this.guideGroup.selectAll('*').remove();
        this.guideStartTime = undefined;
        this.guideEndTime = undefined;
        // Remove custom time markers
        this.axisGroup.selectAll('.time-marker').remove();
        // Redraw the axis to restore all ticks
        this.updateAxis(this.currentTransform ? this.currentTransform.rescaleX(this.xScale) : this.xScale);
    }
}