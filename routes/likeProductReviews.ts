/*
 * Copyright (c) 2014-2024 Bjoern Kimminich & the OWASP Juice Shop contributors.
 * SPDX-License-Identifier: MIT
 */

import challengeUtils = require('../lib/challengeUtils')
import { type Request, type Response, type NextFunction } from 'express'
import { type Review } from '../data/types'
import * as db from '../data/mongodb'
import { challenges } from '../data/datacache'
import { ObjectId } from 'mongodb'
import { isValidObjectId } from 'mongoose'

const security = require('../lib/insecurity')

module.exports = function productReviews () {
  return (req: Request, res: Response, next: NextFunction) => {
    const user = security.authenticatedUsers.from(req)
    
    if (!req.body || typeof req.body.id !== 'string' || !req.body.id.trim()) {
      return res.status(400).json({ error: 'Invalid review ID' })
    }
    const id = req.body.id.trim()
    
    // Validate id is a valid MongoDB ObjectId
    if (!isValidObjectId(id)) {
      return res.status(400).json({ error: 'Invalid review ID format' })
    }
    
    const reviewId = new ObjectId(id)
    db.reviewsCollection.findOne({ _id: reviewId }).then((review: Review) => {
      if (!review) {
        return res.status(404).json({ error: 'Not found' })
      }
      
      const likedBy = review.likedBy
      if (!likedBy.includes(user.data.email)) {
        db.reviewsCollection.updateOne(
          { _id: reviewId, likedBy: { $exists: true } },
          { $inc: { likesCount: 1 } },
          { runValidators: true }
        ).then(() => {
            // Artificial wait for timing attack challenge
            setTimeout(() => {
              db.reviewsCollection.findOne({ _id: reviewId }).then((review: Review) => {
                const likedBy = review.likedBy
                likedBy.push(user.data.email)
                let count = likedBy.filter(email => email === user.data.email).length
                challengeUtils.solveIf(challenges.timingAttackChallenge, () => { return count > 2 })
                
                db.reviewsCollection.updateOne(
                  { _id: reviewId, likedBy: { $exists: true } },
                  { $set: { likedBy } },
                  { runValidators: true }
                ).then(
                  (result: any) => {
                    res.json(result)
                  },
                  (err: unknown) => {
                    res.status(500).json({ error: 'Internal server error' })
                  }
                )
              }).catch(() => {
                res.status(400).json({ error: 'Wrong Params' })
              })
            }, 150)
          },
          (err: unknown) => {
            res.status(500).json({ error: 'Internal server error' })
          }
        )
      } else {
        res.status(403).json({ error: 'Not allowed' })
      }
    }).catch(() => {
      res.status(400).json({ error: 'Wrong Params' })
    })
  }
}
